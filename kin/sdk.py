
import itertools
import json

import rlp
from web3 import Web3, HTTPProvider
from web3.contract import Contract
from web3.utils.encoding import (
    hexstr_if_str,
    to_bytes,
)
from web3.utils.validation import validate_address
from eth_keys import keys
from eth_keys.exceptions import ValidationError
from ethereum.transactions import Transaction
from .exceptions import (
    SdkConfigurationError,
    SdkNotConfiguredError,
)

# production
KIN_CONTRACT_ADDRESS = '0x818fc6c2ec5986bc6e2cbf00939d90556ab12ce5'
KIN_ABI = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_newOwnerCandidate","type":"address"}],"name":"requestOwnershipTransfer","outputs":[],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"isMinting","outputs":[{"name":"","type":"bool"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_amount","type":"uint256"}],"name":"mint","outputs":[],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"type":"function"},{"constant":false,"inputs":[],"name":"acceptOwnership","outputs":[],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"owner","outputs":[{"name":"","type":"address"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"type":"function"},{"constant":true,"inputs":[],"name":"newOwnerCandidate","outputs":[{"name":"","type":"address"}],"payable":false,"type":"function"},{"constant":false,"inputs":[{"name":"_tokenAddress","type":"address"},{"name":"_amount","type":"uint256"}],"name":"transferAnyERC20Token","outputs":[{"name":"success","type":"bool"}],"payable":false,"type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"remaining","type":"uint256"}],"payable":false,"type":"function"},{"constant":false,"inputs":[],"name":"endMinting","outputs":[],"payable":false,"type":"function"},{"anonymous":false,"inputs":[],"name":"MintingEnded","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"spender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_by","type":"address"},{"indexed":true,"name":"_to","type":"address"}],"name":"OwnershipRequested","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_from","type":"address"},{"indexed":true,"name":"_to","type":"address"}],"name":"OwnershipTransferred","type":"event"}]')

DEFAULT_GAS_PER_TX = 90000
DEFAULT_GAS_PRICE = 50 * 10 ** 9  # 50 gwei


class TransactionStatus:
    UNKNOWN = 0
    PENDING = 1
    SUCCESS = 2
    FAIL = 3


class TokenSDK(object):

    def __init__(self, private_key='', provider='', provider_endpoint_uri='https://mainnet.infura.io',
                 contract_address=KIN_CONTRACT_ADDRESS, contract_abi=KIN_ABI):
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

    def get_address(self):
        if not self.address:
            raise SdkNotConfiguredError('address not configured')
        return self.address

    def get_ether_balance(self):
        if not self.address:
            raise SdkNotConfiguredError('address not configured')
        return self.web3.fromWei(self.web3.eth.getBalance(self.address), 'ether')

    def get_token_balance(self):
        if not self.address:
            raise SdkNotConfiguredError('address not configured')
        return self.web3.fromWei(self.token_contract.call().balanceOf(self.address), 'ether')

    def get_address_ether_balance(self, address):
        validate_address(address)
        return self.web3.fromWei(self.web3.eth.getBalance(address), 'ether')

    def get_address_token_balance(self, address):
        validate_address(address)
        return self.web3.fromWei(self.token_contract.call().balanceOf(address), 'ether')

    def send_ether(self, address, amount):
        if not self.address:
            raise SdkNotConfiguredError('address not configured')
        validate_address(address)
        if amount <= 0:
            raise ValueError('amount must be positive')
        raw_tx_hex = self._build_raw_transaction(address, amount)
        return self.web3.eth.sendRawTransaction(raw_tx_hex)

    def send_tokens(self, address, amount):
        if not self.address:
            raise SdkNotConfiguredError('address not configured')
        validate_address(address)
        if amount <= 0:
            raise ValueError('amount must be positive')
        hex_data = self.token_contract._encode_transaction_data('transfer', args=(address, self.web3.toWei(amount, 'ether')))
        data = hexstr_if_str(to_bytes, hex_data)
        raw_tx_hex = self._build_raw_transaction(self.token_contract.address, 0, data)
        return self.web3.eth.sendRawTransaction(raw_tx_hex)

    def get_transaction_status(self, tx_id):
        # transaction status is found in transaction receipt. However, if transaction is pending, a receipt
        # is not available. So first, call getTransaction (which also returns pending transactions),
        # and if transaction is already mined, call getTransactionReceipt.
        tx = self.web3.eth.getTransaction(tx_id)
        if not tx:
            return TransactionStatus.UNKNOWN
        if not tx.get('blockNumber'):
            return TransactionStatus.PENDING

        # transaction is mined
        tx_receipt = self.web3.eth.getTransactionReceipt(tx_id)
        # Byzantium fork introduced a status field
        status = tx_receipt.get('status')
        if status == '0x1':
            return TransactionStatus.SUCCESS
        if status == '0x0':
            return TransactionStatus.FAIL
        # pre-Byzantium, no status field
        # failed transaction usually consumes all the gas
        # TODO: see if the number of block confirmations needs to be taken into account
        if tx_receipt.get('gasUsed') < tx.get('gas'):
            return TransactionStatus.SUCCESS
        # WARNING: there can be cases when gasUsed == gas for successful transactions!
        # In our case however, we create our transactions with fixed gas limit
        return TransactionStatus.FAIL

    def monitor_ether_transactions(self, callback, from_address=None, to_address=None):
        filter_args = self._get_filter_args(from_address, to_address)
        raise NotImplementedError('monitoring of ether transactions is not yet implemented')

    def monitor_token_transactions(self, callback_fn, from_address=None, to_address=None):
        filter_params = {
            'filter': self._get_filter_args(from_address, to_address),
            'toBlock': 'pending',
        }
        transfer_filter = self.token_contract.on('Transfer', filter_params)

        def callback_adapter_fn(entry):
            if entry['blockHash'] == '0x0000000000000000000000000000000000000000000000000000000000000000':
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
            if tx_status > TransactionStatus.PENDING:
                transfer_filter.running = False
                transfer_filter.stopped = True
                self.web3.eth.uninstallFilter(transfer_filter.filter_id)

        transfer_filter.watch(callback_adapter_fn)

    # helpers

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

    def _build_raw_transaction(self, address, amount, data=b''):
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



