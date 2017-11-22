
from decimal import Decimal
import json
import kin
import os
import pytest
import sys
from time import sleep

# Ropsten constants
ROPSTEN_ADDRESS = '0x4c6527c2BEB032D46cfe0648072cAb641cA0aA80'
ROPSTEN_PRIVATE_KEY = 'd60baaa34ed125af0570a3df7d4ad3e80dd5dc5070680573f8de0ecfc1977275'
ROPSTEN_CONTRACT = '0xEF2Fcc998847DB203DEa15fC49d0872C7614910C'
ROPSTEN_CONTRACT_ABI = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_newOwnerCandidate","type":"address"}],"name":"requestOwnershipTransfer","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"issueTokens","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[],"name":"acceptOwnership","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"owner","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"newOwnerCandidate","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"remaining","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"spender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_by","type":"address"},{"indexed":true,"name":"_to","type":"address"}],"name":"OwnershipRequested","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"_from","type":"address"},{"indexed":true,"name":"_to","type":"address"}],"name":"OwnershipTransferred","type":"event"}]')  # noqa: E501
ROPSTEN_PROVIDER_ENDPOINT = 'http://159.89.240.122:8545'  # load balanced parity node

# TestRpc configuration
# the following address is set up in testrpc and is prefilled with eth and tokens.
TESTRPC_ADDRESS = '0x8B455Ab06C6F7ffaD9fDbA11776E2115f1DE14BD'
TESTRPC_PRIVATE_KEY = '0x11c98b8fa69354b26b5db98148a5bc4ef2ebae8187f651b82409f6cefc9bb0b8'
TESTRPC_CONTRACT_FILE = './test/truffle_env/token_contract_address.txt'  # TODO: pass it as environment variable
TESTRPC_ABI_FILE = './test/truffle_env/build/contracts/TestToken.json'
TESTRPC_PROVIDER_ENDPOINT = 'http://localhost:8545'

TEST_KEYFILE = './test/test-keyfile.json'
TEST_PASSWORD = 'password'


@pytest.fixture(scope='session')
def testnet(ropsten):
    class Struct:
        '''handy variable holder'''
        def __init__(self, **entries): self.__dict__.update(entries)

    # if running on Ropsten, return predefined constants.
    if ropsten:
        return Struct(type='ropsten', address=ROPSTEN_ADDRESS, private_key=ROPSTEN_PRIVATE_KEY,
                      contract_address=ROPSTEN_CONTRACT, contract_abi=ROPSTEN_CONTRACT_ABI,
                      provider_endpoint_uri=ROPSTEN_PROVIDER_ENDPOINT)

    # using testrpc, needs truffle build environment.
    # testrpc contract address is set up during truffle deploy, and is passed in a file.
    contract_file = open(TESTRPC_CONTRACT_FILE)
    TESTRPC_CONTRACT = contract_file.read().strip()
    if not TESTRPC_CONTRACT:
        raise ValueError('contract address file {} is empty'.format(TESTRPC_CONTRACT_FILE))

    abi_file = open(TESTRPC_ABI_FILE).read()
    TESTRPC_CONTRACT_ABI = json.loads(abi_file)['abi']

    return Struct(type='testrpc', address=TESTRPC_ADDRESS, private_key=TESTRPC_PRIVATE_KEY,
                  contract_address=TESTRPC_CONTRACT, contract_abi=TESTRPC_CONTRACT_ABI,
                  provider_endpoint_uri=TESTRPC_PROVIDER_ENDPOINT)


def test_create_fail_empty_endpoint(testnet):
    with pytest.raises(kin.SdkConfigurationError, message='either provider or provider endpoint must be provided'):
        kin.TokenSDK(provider_endpoint_uri='')


def test_create_fail_bad_endpoint():
    with pytest.raises(kin.SdkConfigurationError, message='cannot connect to provider endpoint'):
        kin.TokenSDK(provider_endpoint_uri='bad')


def test_create_fail_empty_contract_address():
    with pytest.raises(kin.SdkConfigurationError, message='token contract address not provided'):
        kin.TokenSDK(contract_address='')


def test_create_fail_invalid_contract_address():
    with pytest.raises(kin.SdkConfigurationError, message='invalid token contract address'):
        kin.TokenSDK(contract_address='0xBAD')
    with pytest.raises(kin.SdkConfigurationError, message='invalid token contract address'):
        kin.TokenSDK(contract_address='0x4c6527c2BEB032D46cfe0648072cAb641cA0aA81')  # invalid checksum


def test_create_fail_invalid_abi():
    with pytest.raises(kin.SdkConfigurationError, message='token contract abi not provided'):
        kin.TokenSDK(contract_abi=None)
    with pytest.raises(kin.SdkConfigurationError, message='token contract abi not provided'):
        kin.TokenSDK(contract_abi={})
    with pytest.raises(kin.SdkConfigurationError, message='token contract abi not provided'):
        kin.TokenSDK(contract_abi=[])
    with pytest.raises(kin.SdkConfigurationError, message="invalid token contract abi: 'abi' is not a list"):
        kin.TokenSDK(contract_abi='bad')
    with pytest.raises(kin.SdkConfigurationError, message="invalid token contract abi: The elements of 'abi' "
                                                          "are not all dictionaries"):
        kin.TokenSDK(contract_abi=['bad'])


def test_create_fail_bad_private_key():
    with pytest.raises(kin.SdkConfigurationError, message='cannot load private key: Unexpected private key format.  '
                                                          'Must be length 32 byte string'):
        kin.TokenSDK(private_key='bad')


@pytest.mark.skipif(sys.version_info.major >= 3, reason="not yet supported in python 3")
def test_create_fail_keyfile():
    with pytest.raises(IOError, message="No such file or directory: 'missing.json'"):
        kin.TokenSDK(keyfile='missing.json')
    with open(TEST_KEYFILE, 'w+') as f:
        f.write('not json')
    with pytest.raises(kin.SdkConfigurationError, message="invalid json in keystore file"):
        kin.TokenSDK(keyfile=TEST_KEYFILE)
    with open(TEST_KEYFILE, 'w+') as f:
        f.write('{"key::"value"')
    with pytest.raises(kin.SdkConfigurationError, message="invalid keystore file"):
        kin.TokenSDK(keyfile=TEST_KEYFILE)
    kin.create_keyfile(ROPSTEN_PRIVATE_KEY, TEST_PASSWORD, TEST_KEYFILE)
    with pytest.raises(kin.SdkConfigurationError, message='keyfile decode error: MAC mismatch. Password incorrect?'):
        kin.TokenSDK(keyfile=TEST_KEYFILE, password='wrong')
    os.remove(TEST_KEYFILE)


def test_sdk_not_configured():
    sdk = kin.TokenSDK()
    with pytest.raises(kin.SdkNotConfiguredError, message='address not configured'):
        sdk.get_address()
    with pytest.raises(kin.SdkNotConfiguredError, message='address not configured'):
        sdk.get_ether_balance()
    with pytest.raises(kin.SdkNotConfiguredError, message='address not configured'):
        sdk.get_token_balance()
    with pytest.raises(kin.SdkNotConfiguredError, message='address not configured'):
        sdk.send_ether('address', 100)
    with pytest.raises(kin.SdkNotConfiguredError, message='address not configured'):
        sdk.send_tokens('address', 100)


def test_create_default():
    sdk = kin.TokenSDK()
    assert sdk
    assert sdk.web3
    assert sdk.token_contract
    assert not sdk.private_key and not sdk.address


def test_create_with_private_key(testnet):
    sdk = kin.TokenSDK(private_key=testnet.private_key)
    assert sdk
    assert sdk.web3
    assert sdk.token_contract
    assert sdk.private_key == testnet.private_key
    assert sdk.get_address() == testnet.address


@pytest.mark.skipif(sys.version_info.major >= 3, reason="not yet supported in python 3")
def test_create_with_keyfile():
    kin.create_keyfile(ROPSTEN_PRIVATE_KEY, TEST_PASSWORD, TEST_KEYFILE)
    sdk = kin.TokenSDK(keyfile=TEST_KEYFILE, password=TEST_PASSWORD)
    assert sdk
    assert sdk.web3
    assert sdk.token_contract
    assert sdk.private_key == ROPSTEN_PRIVATE_KEY
    assert sdk.get_address() == ROPSTEN_ADDRESS
    os.remove(TEST_KEYFILE)


@pytest.fixture
def test_sdk(testnet):
    sdk = kin.TokenSDK(provider_endpoint_uri=testnet.provider_endpoint_uri, private_key=testnet.private_key,
                       contract_address=testnet.contract_address, contract_abi=testnet.contract_abi)
    assert sdk
    assert sdk.web3
    assert sdk.token_contract
    assert sdk.private_key == testnet.private_key
    assert sdk.get_address() == testnet.address
    return sdk


def test_get_address(test_sdk, testnet):
    assert test_sdk.get_address() == testnet.address


def test_get_ether_balance(test_sdk):
    balance = test_sdk.get_ether_balance()
    assert balance > 0


def test_get_address_ether_balance(test_sdk, testnet):
    with pytest.raises(ValueError, message="'0xBAD' is not an address"):
        test_sdk.get_address_ether_balance('0xBAD')
    balance = test_sdk.get_address_ether_balance(testnet.address)
    assert balance > 0


def test_get_token_balance(test_sdk):
    balance = test_sdk.get_token_balance()
    assert balance > 0


def test_get_address_token_balance(test_sdk, testnet):
    with pytest.raises(ValueError, message="'0xBAD' is not an address"):
        test_sdk.get_address_token_balance('0xBAD')
    balance = test_sdk.get_address_token_balance(testnet.address)
    assert balance > 0


def test_send_ether_fail(test_sdk, testnet):
    with pytest.raises(ValueError, message='amount must be positive'):
        test_sdk.send_ether(testnet.address, 0)
    with pytest.raises(ValueError, message='insufficient funds for gas * price + value'):
        test_sdk.send_ether(testnet.address, 100)


def test_send_tokens_fail(test_sdk, testnet):
    with pytest.raises(ValueError, message='amount must be positive'):
        test_sdk.send_tokens(testnet.address, 0)

    # NOTE: sending more tokens than available will not cause immediate exception like with ether,
    # but will result in failed onchain transaction


def test_get_transaction_status(test_sdk, testnet):
    # unknown
    tx_status = test_sdk.get_transaction_status('0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef')
    assert tx_status == kin.TransactionStatus.UNKNOWN

    # some tests for Ropsten only
    if testnet.type == 'ropsten':
        # successful ether transfer
        tx_status = test_sdk.get_transaction_status('0x86d51e5547b714232d39e86e86295c20e0241f38d9b828c080cc1ec561f34daf')
        assert tx_status == kin.TransactionStatus.SUCCESS
        # successful token transfer
        tx_status = test_sdk.get_transaction_status('0xb5101d58c1e51271837b5343e606b751512882e4f4b175b2f6dae68b7a42d4ab')
        assert tx_status == kin.TransactionStatus.SUCCESS
        # failed token transfer
        tx_status = test_sdk.get_transaction_status('0x7a3f2c843a04f6050258863dbea3fec3651b107baa5419e43adb6118478da36b')
        assert tx_status == kin.TransactionStatus.FAIL


def test_get_transaction_data(test_sdk, testnet):
    tx_data = test_sdk.get_transaction_data('0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef')
    assert tx_data.status == kin.TransactionStatus.UNKNOWN

    # some tests for Ropsten only
    if testnet.type == 'ropsten':
        # check ether transaction
        tx_id = '0x86d51e5547b714232d39e86e86295c20e0241f38d9b828c080cc1ec561f34daf'
        tx_data = test_sdk.get_transaction_data(tx_id)
        assert tx_data.status == kin.TransactionStatus.SUCCESS
        assert tx_data.from_address.lower() == testnet.address.lower()
        assert tx_data.to_address.lower() == testnet.address.lower()
        assert tx_data.ether_amount == 0.001
        assert tx_data.token_amount == 0
        # check the number of confirmations
        tx = test_sdk.web3.eth.getTransaction(tx_id)
        assert tx and tx.get('blockNumber')
        tx_block_number = int(tx['blockNumber'])
        cur_block_number = int(test_sdk.web3.eth.blockNumber)
        calc_confirmations = cur_block_number - tx_block_number + 1
        tx_data = test_sdk.get_transaction_data(tx_id)
        assert tx_data.num_confirmations == calc_confirmations or tx_data.num_confirmations == calc_confirmations + 1


def test_monitor_ether_transactions(test_sdk, testnet):
    tx_statuses = {}

    def my_callback(tx_id, status, from_address, to_address, amount):
        if tx_id not in tx_statuses:  # not mine, skip it
            return
        assert from_address.lower() == testnet.address.lower()
        assert to_address.lower() == testnet.address.lower()
        assert amount == Decimal('0.001')
        tx_statuses[tx_id] = status

    with pytest.raises(ValueError, message='either from_address or to_address or both must be provided'):
        test_sdk.monitor_ether_transactions(my_callback)

    # start monitoring ether transactions
    test_sdk.monitor_ether_transactions(my_callback, from_address=testnet.address)

    # successful ether transfer
    tx_id = test_sdk.send_ether(testnet.address, 0.001)
    tx_statuses[tx_id] = kin.TransactionStatus.UNKNOWN

    for wait in range(0, 30000):
        if tx_statuses[tx_id] > kin.TransactionStatus.UNKNOWN:
            break
        sleep(0.001)
    assert tx_statuses[tx_id] >= kin.TransactionStatus.PENDING
    tx_data = test_sdk.get_transaction_data(tx_id)
    assert tx_data.status >= kin.TransactionStatus.PENDING
    assert tx_data.from_address.lower() == testnet.address.lower()
    assert tx_data.to_address.lower() == testnet.address.lower()
    assert tx_data.ether_amount == 0.001
    assert tx_data.token_amount == 0
    assert tx_data.num_confirmations >= 0

    for wait in range(0, 90):
        if tx_statuses[tx_id] > kin.TransactionStatus.PENDING:
            break
        sleep(1)
    assert tx_statuses[tx_id] == kin.TransactionStatus.SUCCESS
    tx_data = test_sdk.get_transaction_data(tx_id)
    assert tx_data.num_confirmations == 1


def test_monitor_token_transactions(test_sdk, testnet):
    tx_statuses = {}

    def my_callback(tx_id, status, from_address, to_address, amount):
        if tx_id not in tx_statuses:  # not mine, skip it
            return
        assert from_address.lower() == testnet.address.lower()
        assert to_address.lower() == testnet.address.lower()
        tx_statuses[tx_id] = status

    with pytest.raises(ValueError, message='either from_address or to_address or both must be provided'):
        test_sdk.monitor_token_transactions(my_callback)

    # start monitoring token transactions from my address
    test_sdk.monitor_token_transactions(my_callback, to_address=testnet.address)

    # transfer more than available.
    # NOTE: with a standard ethereum node (geth, parity, etc), this will result in a failed onchain transaction.
    # With testrpc, this results in ValueError exception instead.
    if testnet.type == 'testrpc':
        with pytest.raises(ValueError, message='VM Exception while processing transaction: invalid opcode'):
            test_sdk.send_tokens(testnet.address, 10000000)
    else:
        tx_id = test_sdk.send_tokens(testnet.address, 10000000)
        tx_statuses[tx_id] = kin.TransactionStatus.UNKNOWN

        for wait in range(0, 30000):
            if tx_statuses[tx_id] > kin.TransactionStatus.UNKNOWN:
                break
            sleep(0.001)
        assert tx_statuses[tx_id] == kin.TransactionStatus.PENDING

        for wait in range(0, 90):
            if tx_statuses[tx_id] > kin.TransactionStatus.PENDING:
                break
            sleep(1)
        assert tx_statuses[tx_id] == kin.TransactionStatus.FAIL

    # successful token transfer
    tx_id = test_sdk.send_tokens(testnet.address, 10)
    tx_statuses[tx_id] = kin.TransactionStatus.UNKNOWN

    # wait for transaction status change
    for wait in range(0, 30000):
        if tx_statuses[tx_id] > kin.TransactionStatus.UNKNOWN:
            break
        sleep(0.001)
    assert tx_statuses[tx_id] >= kin.TransactionStatus.PENDING
    tx_data = test_sdk.get_transaction_data(tx_id)
    assert tx_data.status >= kin.TransactionStatus.PENDING
    assert tx_data.from_address.lower() == testnet.address.lower()
    assert tx_data.to_address.lower() == testnet.address.lower()
    assert tx_data.ether_amount == 0
    assert tx_data.token_amount == 10
    assert tx_data.num_confirmations >= 0

    # test transaction status
    tx_status = test_sdk.get_transaction_status(tx_id)
    assert tx_status >= kin.TransactionStatus.PENDING

    # wait for transaction status change
    for wait in range(0, 90):
        if tx_statuses[tx_id] > kin.TransactionStatus.PENDING:
            break
        sleep(1)
    assert tx_statuses[tx_id] == kin.TransactionStatus.SUCCESS
    tx_status = test_sdk.get_transaction_status(tx_id)
    assert tx_status == kin.TransactionStatus.SUCCESS
    tx_data = test_sdk.get_transaction_data(tx_id)
    assert tx_data.num_confirmations == 1
