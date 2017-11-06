
# Kin Python SDK 

## Requirements.

Make sure you have Python 2 >=2.7.9.

## Installation 

```sh
pip install git+https://github.com/kinfoundation/kin-sdk-python.git
```

## Usage

### Initialization
```python
import kin

# Init SDK with default parameters
# default parameters:
#   provider_endpoint_uri is https://mainnet.infura.io
#   contract_address is KIN production contract 0x818fc6c2ec5986bc6e2cbf00939d90556ab12ce5
#   contract_abi is KIN production contract ABI
# Note: this is useful for generic blockchain access, when public key is not needed.
kin_sdk = kin.TokenSDK()

# Init SDK with my private key and default parameters
kin_sdk = kin.TokenSDK(private_key='a60baaa34ed125af0570a3df7d4cd3e80dd5dc5070680573f8de0ecfc1957575')

# Init SDK with custom parameters
kin_sdk = kin.TokenSDK(provider_endpoint_uri='json-rpc endpoint uri', private_key='my private key',
                       contract_address='my contract address', contract_abi='abi of my contract as json')
````

### Get Wallet Details
```python
# Get my public address
address = kin_sdk.get_address()
```

### Getting Balance
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
# Send Ether from my account to some address
tx_id = kin_sdk.send_ether('address', 10)

# Send KIN from my account to some address
tx_id = kin_sdk.send_tokens('address', 10)
```

### Transaction Monitoring
```python
# Get transaction status
tx_status = kin_sdk.get_transaction_status(tx_id)
# returns one of:
#   kin.TransactionStatus.UNKNOWN
#   kin.TransactionStatus.PENDING
#   kin.TransactionStatus.SUCCESS
#   kin.TransactionStatus.FAIL

# Setup monitoring callback
tx_statuses = {}
def mycallback(tx_id, status, from_address, to_address, amount):
    tx_statuses[tx_id] = status
  
# Monitor KIN transactions from me 
kin_sdk.monitor_token_transactions(mycallback, from_address=kin_sdk.get_address())

# Send tokens
tx_id = kin_sdk.send_tokens('to address', 10)

# In a second or two, the transaction enters the pending queue
sleep(2)
assert tx_statuses[tx_id] == kin.TransactionStatus.PENDING

# Wait until the transaction is confirmed 
waited = 0
while tx_statuses[tx_id] == kin.TransactionStatus.PENDING and waited <= 60:
    sleep(10)
    waited += 10
assert tx_statuses[tx_id] == kin.TransactionStatus.SUCCESS
```

## Support & Discussion

## License
Code released under [MIT LICENSE](LICENSE)  

## Contributions 
 Pull requests and new issues are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for details. 
 
