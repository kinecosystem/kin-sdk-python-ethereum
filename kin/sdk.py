# -*- coding: utf-8 -*

# Copyright (C) 2017 Kin Foundation

"""
The :class:`~kin.TokenSDK` class is the primary interface to the KIN Python SDK.
It maintains a context for a connection with an Ethereum JSON-RPC node and hides
all the specifics of dealing with Ethereum JSON-RPC API.
"""

import json
from time import sleep

from eth_abi import decode_abi
from eth_keys import keys
from eth_keys.exceptions import ValidationError
from eth_utils import function_signature_to_4byte_selector
from ethereum.transactions import Transaction

import rlp
from web3 import Web3, HTTPProvider
from web3.contract import Contract
from web3.utils.encoding import (
    hexstr_if_str,
    to_bytes,
    to_hex,
)
from eth_utils.hexidecimal import encode_hex
from web3.utils.validation import validate_address

from .exceptions import (
    SdkConfigurationError,
    SdkNotConfiguredError,
)

import logging
logger = logging.getLogger(__name__)


# KIN production contract.
KIN_CONTRACT_ADDRESS = '0x818fc6c2ec5986bc6e2cbf00939d90556ab12ce5'
KIN_ABI = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_newOwnerCandidate","type":"address"}],"name":"requestOwnershipTransfer","outputs":[],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"isMinting","outputs":[{"name":"","type":"bool"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_amount","type":"uint256"}],"name":"mint","outputs":[],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"type":"function"},{"constant":false,"inputs":[],"name":"acceptOwnership","outputs":[],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"owner","outputs":[{"name":"","type":"address"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"newOwnerCandidate","outputs":[{"name":"","type":"address"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_tokenAddress","type":"address"},{"name":"_amount","type":"uint256"}],"name":"transferAnyERC20Token","outputs":[{"name":"success","type":"bool"}],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"remaining","type":"uint256"}],"payable":false,"type":"function"},{"constant":false,"inputs":[],"name":"endMinting","outputs":[],"payable":false,"type":"function"},{"anonymous":false,"inputs":[],"name":"MintingEnded","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"spender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_by","type":"address"},{"indexed":true,"name":"_to","type":"address"}],"name":"OwnershipRequested","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_from","type":"address"},{"indexed":true,"name":"_to","type":"address"}],"name":"OwnershipTransferred","type":"event"}]')  # noqa: E501

# ERC20 contract consts.
# ERC20_TRANSFER_ABI_PREFIX = to_hex(function_signature_to_4byte_selector('transfer(address, uint256)'))
ERC20_TRANSFER_ABI_PREFIX = encode_hex(function_signature_to_4byte_selector('transfer(address, uint256)'))

# default gas configuration.
DEFAULT_GAS_PER_TX = 90000
DEFAULT_GAS_PRICE = 50 * 10 ** 9  # 50 gwei

# default request retry configuration.
RETRY_ATTEMPTS = 3
RETRY_DELAY = 0.3


# noinspection PyClassHasNoInit
class TransactionStatus:
    """Transaction status enumerator."""
    UNKNOWN = 0
    PENDING = 1
    SUCCESS = 2
    FAIL = 3


class TokenSDK(object):

    def __init__(self, private_key='', provider='', provider_endpoint_uri='https://mainnet.infura.io',
                 contract_address=KIN_CONTRACT_ADDRESS, contract_abi=KIN_ABI):
        """Create a new instance of the KIN SDK.

        The SDK needs a JSON-RPC provider, contract definitions and the wallet private key.
        The user may pass either a provider or a provider endpoint URI, in which case a default
        `web3:providers:HTTPProvider` will be created.

        If private_key is not provided, the SDK can still be used in "anonymous" mode with only the following
        functions available:
            - get_address_ether_balance
            - get_transaction_status
            - monitor_ether_transactions

        :param str private_key: a private key to initialize the wallet with. If not provided,
            the wallet will not be initialized and methods needing the wallet will raise exception.

        :param provider: JSON-RPC provider to work with. If not provided, a default `web3:providers:HTTPProvider`
            is used, inited with provider_endpoint_uri.
        :type provider: :class:`web3:providers:BaseProvider`

        :param str provider_endpoint_uri: a URI to use with a default HTTPProvider. If not provided, a
            default endpoint will be used.

        :param str contract_address: the address of the token contract. If not provided, a default KIN
            contract address will be used.

        :param dict contract_abi: The contract ABI. If not provided, a default KIN contract ABI will be used.

        :returns: An instance of the SDK.
        :rtype: :class:`~kin.TokenSDK`

        :raises: :class:`~kin.exceptions.SdkConfigurationError` if some of the configuration parameters are invalid.
        """

        if not provider and not provider_endpoint_uri:
            raise SdkConfigurationError('either provider or provider endpoint must be provided')

        if not contract_address:
            raise SdkConfigurationError('token contract address not provided')

        try:
            validate_address(contract_address)
        except ValueError:
            raise SdkConfigurationError('invalid token contract address')

        if not contract_abi:
            raise SdkConfigurationError('token contract abi not provided')

        if provider:
            self.web3 = Web3(provider)
        else:
            self.web3 = Web3(HTTPProvider(provider_endpoint_uri))
        if not self.web3.isConnected():
            raise SdkConfigurationError('cannot connect to provider endpoint')

        self.token_contract = self.web3.eth.contract(contract_address, abi=contract_abi, ContractFactoryClass=Contract)
        self.private_key = None
        self.address = None

        if private_key:
            try:
                private_key_bytes = hexstr_if_str(to_bytes, private_key)
                pk = keys.PrivateKey(private_key_bytes)
            except ValidationError as e:
                raise SdkConfigurationError('cannot load private key: ' + str(e))
            self.private_key = private_key
            self.address = self.web3.eth.defaultAccount = pk.public_key.to_checksum_address()

        # ethereum transactions monitoring
        self._pending_tx_filter = None
        self._pending_tx_monitor = {
            'all': {}
        }
        self._new_block_filter = None

    def get_address(self):
        """Get public address of the SDK wallet.
        The wallet is configured by a private key supplied in during SDK initialization.

        :returns: public address of the wallet.
        :rtype: str

        :raises: :class:`~kin.exceptions.SdkConfigurationError`: if the SDK was not configured with a private key.
        """
        if not self.address:
            raise SdkNotConfiguredError('address not configured')
        return self.address

    def get_ether_balance(self):
        """Get Ether balance of the SDK wallet.
        The wallet is configured by a private key supplied in during SDK initialization.

        :returns: : the balance in Ether of the internal wallet.
        :rtype: Decimal

        :raises: :class:`~kin.exceptions.SdkConfigurationError`: if the SDK was not configured with a private key.
        """
        if not self.address:
            raise SdkNotConfiguredError('address not configured')
        return self.web3.fromWei(self.web3.eth.getBalance(self.address), 'ether')

    def get_token_balance(self):
        """Get KIN balance of the SDK wallet.
        The wallet is configured by a private key supplied in during SDK initialization.

        :returns: : the balance in KIN of the internal wallet.
        :rtype: Decimal

        :raises: :class:`~kin.exceptions.SdkConfigurationError`: if the SDK was not configured with a private key.
        """
        if not self.address:
            raise SdkNotConfiguredError('address not configured')
        return self.web3.fromWei(self.token_contract.call().balanceOf(self.address), 'ether')

    def get_address_ether_balance(self, address):
        """Get Ether balance of a public address.

        :param: str address: a public address to query.

        :returns: the balance in Ether of the provided address.
        :rtype: Decimal

        :raises: ValueError: if the supplied address has a wrong format.
        """
        validate_address(address)
        return self.web3.fromWei(self.web3.eth.getBalance(address), 'ether')

    def get_address_token_balance(self, address):
        """Get KIN balance of a public address.

        :param: str address: a public address to query.

        :returns: : the balance in KIN of the provided address.
        :rtype: Decimal

        :raises: ValueError: if the supplied address has a wrong format.
        """
        validate_address(address)
        return self.web3.fromWei(self.token_contract.call().balanceOf(address), 'ether')

    def send_ether(self, address, amount):
        """Send Ether from my wallet to address.

        :param str address: the address to send Ether to.

        :param float amount: the amount of Ether to transfer.

        :return: transaction id
        :rtype: str

        :raises: :class:`~kin.exceptions.SdkConfigurationError`: if the SDK was not configured with a private key.
        :raises: ValueError: if the amount is not positive.
        :raises: ValueError: if the nonce is incorrect.
        :raises: ValueError if insufficient funds for for gas * price + value.
        """
        if not self.address:
            raise SdkNotConfiguredError('address not configured')
        validate_address(address)
        if amount <= 0:
            raise ValueError('amount must be positive')
        return self._send_raw_transaction(address, amount)

    def send_tokens(self, address, amount):
        """Send tokens from my wallet to address.

        :param str address: the address to send tokens to.

        :param float amount: the amount of tokens to transfer.

        :returns: transaction id
        :rtype: str

        :raises: :class:`~kin.exceptions.SdkConfigurationError`: if the SDK was not configured with a private key.
        :raises: ValueError: if the amount is not positive.
        :raises: ValueError: if the nonce is incorrect.
        :raises: ValueError if insufficient funds for for gas * price.
        """
        if not self.address:
            raise SdkNotConfiguredError('address not configured')
        validate_address(address)
        if amount <= 0:
            raise ValueError('amount must be positive')
        hex_data = self.token_contract._encode_transaction_data('transfer', args=(address, self.web3.toWei(amount, 'ether')))
        data = hexstr_if_str(to_bytes, hex_data)
        return self._send_raw_transaction(self.token_contract.address, 0, data)

    def get_transaction_status(self, tx_id):
        """Get the transaction status.

        :param str tx_id: transaction id (hash).

        :returns: transaction status.
        :rtype: `~kin.TransactionStatus`
        """
        tx = self.web3.eth.getTransaction(tx_id)
        if not tx:
            return TransactionStatus.UNKNOWN
        return self._get_tx_status(tx)

    def monitor_ether_transactions(self, callback_fn, from_address=None, to_address=None):
        """Monitors Ether transactions and calls back on transactions matching the supplied filter.

        :param callback_fn: the callback function with the signature `func(tx_id, status, from_address, to_address, amount)`

        :param str from_address: the transactions must originate from this address. If not provided,
            all addresses will match.

        :param str to_address: the transactions must be sent to this address. If not provided,
            all addresses will match.
        """
        filter_args = self._get_filter_args(from_address, to_address)

        def check_and_callback(tx, status):
            if tx.get('input') and tx['input'] != '0x0':  # this is a contract transaction, skip it
                return
            if ('from' in filter_args and tx['from'].lower() == filter_args['from'].lower() and
                    ('to' not in filter_args or tx['to'].lower() == filter_args['to'].lower()) or
                    ('to' in filter_args and tx['to'].lower() == filter_args['to'].lower())):
                callback_fn(tx['hash'], status, tx['from'], tx['to'], self.web3.fromWei(tx['value'], 'ether'))

        def pending_tx_callback_adapter_fn(tx_id):
            tx = self.web3.eth.getTransaction(tx_id)
            check_and_callback(tx, TransactionStatus.PENDING)

        def new_block_callback_adapter_fn(block_id):
            block = self.web3.eth.getBlock(block_id, True)
            for tx in block['transactions']:
                check_and_callback(tx, TransactionStatus.SUCCESS)  # TODO: number of block confirmations

        if not self._pending_tx_filter:
            self._pending_tx_filter = self.web3.eth.filter('pending')
        self._pending_tx_filter.watch(pending_tx_callback_adapter_fn)

        if not self._new_block_filter:
            self._new_block_filter = self.web3.eth.filter('latest')
        self._new_block_filter.watch(new_block_callback_adapter_fn)

    def monitor_token_transactions(self, callback_fn, from_address=None, to_address=None):
        """Monitors token transactions and calls back on transactions matching the supplied filter.

        :param callback_fn: the callback function with the signature `func(tx_id, status, from_address, to_address, amount)`

        :param str from_address: the transactions must originate from this address. If not provided,
            all addresses will match.

        :param str to_address: the transactions must be sent to this address. If not provided,
            all addresses will match. Note that token transactions are always sent to the contract, and the real
            recipient is found in transaction data. This function will decode the data and return the correct
            recipient address.
        """
        filter_args = self._get_filter_args(from_address, to_address)

        '''Not used: event log filtering.
        filter_params = {
            'filter': filter_args,
            'toBlock': 'pending',
        }
        transfer_filter = self.token_contract.on('Transfer', filter_params)
        transfer_filter.watch(log_callback_adapter_fn)

        def log_callback_adapter_fn(entry):
            if not entry['blockHash'] or entry['blockHash'] == '0x0000000000000000000000000000000000000000000000000000000000000000':
                tx_status = TransactionStatus.PENDING
            else:
                tx_status = TransactionStatus.SUCCESS  # TODO: how to determine FAIL
            tx_id = entry.get('transactionHash')
            tx_from = entry['args'].get('from')
            tx_to = entry['args'].get('to')
            amount = self.web3.fromWei(entry['args'].get('value'), 'ether')
            callback_fn(tx_id, tx_status, tx_from, tx_to, amount)

            # stop watching when the transaction is successful or failed.
            # NOTE: transfer_filter.stop_watching() causes thread exception because of 'current thread join'
            # So we are doing what is needed explicitly here.
            # TODO: change this when taking into account the number of block confirmations
            #if tx_status > TransactionStatus.PENDING:
            #    transfer_filter.running = False
            #    transfer_filter.stopped = True
            #    self.web3.eth.uninstallFilter(transfer_filter.filter_id)
        '''

        def pending_tx_callback_adapter_fn(tx_id):
            tx = self.web3.eth.getTransaction(tx_id)
            ok, tx_from, tx_to, amount = self._check_parse_contract_tx(tx, filter_args)
            if ok:
                callback_fn(tx['hash'], TransactionStatus.PENDING, tx_from, tx_to, amount)

        def new_block_callback_adapter_fn(block_id):
            block = self.web3.eth.getBlock(block_id, True)
            for tx in block['transactions']:
                ok, tx_from, tx_to, amount = self._check_parse_contract_tx(tx, filter_args)
                if ok:
                    status = self._get_tx_status(tx)
                    callback_fn(tx['hash'], status, tx_from, tx_to, amount)

        if not self._pending_tx_filter:
            self._pending_tx_filter = self.web3.eth.filter('pending')
        self._pending_tx_filter.watch(pending_tx_callback_adapter_fn)

        if not self._new_block_filter:
            self._new_block_filter = self.web3.eth.filter('latest')
        self._new_block_filter.watch(new_block_callback_adapter_fn)

    # helpers

    def _get_tx_status(self, tx):
        """Determines transaction status.

        :param dict tx: transaction object

        :returns: the status of this transaction.
        :rtype: `kin.TransactionStatus`
        """
        if not tx.get('blockNumber'):
            return TransactionStatus.PENDING

        # transaction is mined
        tx_receipt = self.web3.eth.getTransactionReceipt(tx['hash'])

        # Byzantium fork introduced a status field
        status = tx_receipt.get('status')
        if status == '0x1':
            return TransactionStatus.SUCCESS
        if status == '0x0':
            return TransactionStatus.FAIL

        # pre-Byzantium, no status field
        # failed transaction usually consumes all the gas
        if tx_receipt.get('gasUsed') < tx.get('gas'):
            return TransactionStatus.SUCCESS  # TODO: number of block confirmations
        # WARNING: there can be cases when gasUsed == gas for successful transactions!
        # In our case however, we create our transactions with fixed gas limit
        return TransactionStatus.FAIL

    def _check_parse_contract_tx(self, tx, filter_args):
        """Parse contract transaction and check whether it matches the supplied filter.
        If the transaction matches the filter, the first returned value will be True, and the rest will be
        correctly filled. If there is no match, the first returned value is False and the rest are empty.

        :param dict tx: transaction object

        :param dict filter_args: a filter that contains fields 'to', 'from' or both.

        :returns: matching status, from address, to address, token amount
        """
        if not tx.get('to') or tx['to'].lower() != self.token_contract.address.lower():  # must be sent to our contract
            return False, '', '', 0
        if not tx.get('input') or tx['input'] == '0x':  # not a contract transaction
            return False, '', '', 0
        if not tx['input'].startswith(ERC20_TRANSFER_ABI_PREFIX):  # only interested in calls to 'transfer' method
            return False, '', '', 0

        to, amount = decode_abi(['uint256', 'uint256'], tx['input'][len(ERC20_TRANSFER_ABI_PREFIX):])
        to = to_hex(to)
        amount = self.web3.fromWei(amount, 'ether')
        if ('from' in filter_args and tx['from'].lower() == filter_args['from'].lower() and
                ('to' not in filter_args or to.lower() == filter_args['to'].lower()) or
                ('to' in filter_args and to.lower() == filter_args['to'].lower())):
            return True, tx['from'], to, amount
        return False, '', '', 0

    def _send_raw_transaction(self, address, amount, data=b''):
        """Send transaction with retry.
        Submitting a raw transaction can result in a nonce collision error. In this case, the submission is
        retried with a new nonce.

        :param str address: the target address.

        :param float amount: the amount of Ether to send.

        :param data: binary data to put into transaction data field.

        :returns: transaction id (hash)
        :rtype: str
        """
        attempts = 0
        while True:
            try:
                raw_tx_hex = self._build_raw_transaction(address, amount, data)
                return self.web3.eth.sendRawTransaction(raw_tx_hex)
            except ValueError as ve:
                if 'message' in ve.args[0] \
                        and ('nonce too low' in ve.args[0]['message']
                             or 'another transaction with same nonce' in ve.args[0]['message']) \
                        and attempts < RETRY_ATTEMPTS:
                    logging.warning('transaction nonce error, retrying')
                    attempts += 1
                    sleep(RETRY_DELAY)  # TODO: exponential backoff, configurable retry
                    continue
                raise

    def _build_raw_transaction(self, address, amount, data=b''):
        """Builds a raw transaction string.

        :param str address: the target address.

        :param float amount: the amount of Ether to send.

        :param data: binary data to put into transaction.

        :returns: a raw transaction as a string of hex chars.
        :rtype: str
        """
        nonce = self.web3.eth.getTransactionCount(self.address, 'pending')
        # TODO: replace pyethereum code with the newer code in web3.py (v4) and remove pyethereum from requirements.
        tx = Transaction(
            nonce=nonce,
            gasprice=DEFAULT_GAS_PRICE,   # TODO: optimal gas price
            startgas=DEFAULT_GAS_PER_TX,  # TODO: optimal gas limit
            to=address,
            value=self.web3.toWei(amount, 'ether'),
            data=data,
        ).sign(self.private_key)
        return self.web3.toHex(rlp.encode(tx))

    @staticmethod
    def _get_filter_args(from_address, to_address):
        if not from_address and not to_address:
            raise ValueError('either from_address or to_address or both must be provided')
        filter_args = {}
        if from_address:
            validate_address(from_address)
            filter_args['from'] = from_address
        if to_address:
            validate_address(to_address)
            filter_args['to'] = to_address
        return filter_args



