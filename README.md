
# Kin Python SDK 
[![Build Status](https://travis-ci.org/kinfoundation/kin-sdk-python.svg)](https://travis-ci.org/kinfoundation/kin-sdk-python) [![Coverage Status](https://codecov.io/gh/kinfoundation/kin-sdk-python/branch/master/graph/badge.svg)](https://codecov.io/gh/kinfoundation/kin-sdk-python)

## End-of-Life

This SDK is no longer supported for new users. Please see [kin-core-python](https://github.com/kinfoundation/kin-core-python) for the current SDK.

## Requirements.

Make sure you have Python 2 >=2.7.9.

## Installation 

```sh
pip install git+https://github.com/kinfoundation/kin-sdk-python.git
```

### Installation in Google App Engine Python Standard Environment
[GAE Python Standard environment](https://cloud.google.com/appengine/docs/standard/) executes Python 
application code using a pre-loaded Python interpreter in a safe sandboxed environment. The interpreter cannot 
load Python services with C code; it is a "pure" Python environment. However, the required
[web3 package](https://pypi.python.org/pypi/web3/) requires other packages that are natively implemented, namely
[pysha3](https://pypi.python.org/pypi/pysha3) and [cytoolz](https://pypi.python.org/pypi/cytoolz).
In order to overcome this limitation, do the following:
1. Replace the `sha3.py` installed by pysha3 with the [attached sha3.py](sha3.py.alt).
2. Replace the installed `cytoolz` package with the `toolz` package.


## Usage

### Initialization

```python
import kin

# Init SDK with default parameters
# default parameters:
#   `provider` is `web3.providers.HTTPProvider`
#   `provider_endpoint_uri` is `http://159.89.240.147:8545`
#   `contract_address` is KIN production contract `0x818fc6c2ec5986bc6e2cbf00939d90556ab12ce5`
#   `contract_abi` is KIN production contract ABI
# Note: this is useful for anonymous blockchain access, when your private key is not needed.
kin_sdk = kin.TokenSDK()

# Init SDK with my private key and default parameters
kin_sdk = kin.TokenSDK(private_key='a60baaa34ed125af0570a3df7d4cd3e80dd5dc5070680573f8de0ecfc1957575')

# Init SDK with my keyfile and default parameters
# First, create a keyfile from my private key
kin.create_keyfile('a60baaa34ed125af0570a3df7d4cd3e80dd5dc5070680573f8de0ecfc1957575', 'my password', 'keyfile.json')
# Init SDK with this keyfile
kin_sdk = kin.TokenSDK(keyfile='keyfile.json', password='my password')

# Init SDK with custom parameters
kin_sdk = kin.TokenSDK(provider_endpoint_uri='JSON-RPC endpoint URI', private_key='my private key',
                       contract_address='my contract address', contract_abi='abi of my contract as json')
````
For more examples, see the [SDK test file](test/test_sdk.py). The file also contains pre-defined values for testing
with testrpc and Ropsten.


### Get Wallet Details
```python
# Get my public address. The address is derived from the private key the SDK was inited with.
address = kin_sdk.get_address()
```

### Getting Account Balance
```python
# Get Ether balance of my account
eth_balance = kin_sdk.get_ether_balance()

# Get KIN balance of my account
kin_balance = kin_sdk.get_token_balance()

# Get Ether balance of some address
eth_balance = kin_sdk.get_address_ether_balance('address')

# Get KIN balance of some address
kin_balance = kin_sdk.get_address_token_balance('address')
```

### Sending Coin
```python
# Send Ether from my account to some address. The amount is in Ether.
tx_id = kin_sdk.send_ether('address', 10)

# Send KIN from my account to some address. The amount is in KIN.
tx_id = kin_sdk.send_tokens('address', 10)
```

### Transaction Monitoring
```python
# Get transaction status
tx_status = kin_sdk.get_transaction_status(tx_id)
# Returns one of:
#   kin.TransactionStatus.UNKNOWN
#   kin.TransactionStatus.PENDING
#   kin.TransactionStatus.SUCCESS
#   kin.TransactionStatus.FAIL

# Get transaction details
tx_data = kin_sdk.get_transaction_data(tx_id)
# Returns a kin.TransactionData object containing the following fields:
# from_address - the address this transaction was sent from
# to_address   - the address this transaction was sent to. For token transactions, this is the decoded recipient address.
# ether_amount - the amount of transferred Ether. 0 for token transactions.
# token_amount - the amount of transferred tokens. 0 for Ether transactions.
# status       - the transaction status, see above.
# num_confirmations - the number of confirmations for this transaction:
#   -1 if transaction is not found
#    0 if transaction is pending
#   >0 if transaction is confirmed

# Setup monitoring callback
tx_statuses = {}
def mycallback(tx_id, status, from_address, to_address, amount):
    tx_statuses[tx_id] = status
  
# Monitor KIN transactions from me 
kin_sdk.monitor_token_transactions(mycallback, from_address=kin_sdk.get_address())

# Send tokens
tx_id = kin_sdk.send_tokens('to address', 10)

# In a second or two, the transaction enters the pending queue
for wait in range(0, 5000):
    if tx_statuses[tx_id] > kin.TransactionStatus.UNKNOWN:
        break
    sleep(0.001)
assert tx_statuses[tx_id] >= kin.TransactionStatus.PENDING

# Wait until transaction is confirmed 
for wait in range(0, 90):
    if tx_statuses[tx_id] > kin.TransactionStatus.PENDING:
        break
    sleep(1)
assert tx_statuses[tx_id] == kin.TransactionStatus.SUCCESS
```

## Support & Discussion

## License
Code released under [GPLv2 license](LICENSE)

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for SDK contributing guidelines. 

