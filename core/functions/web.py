import requests

def get_real_nonce(address: str, rpc_url: str):
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getTransactionCount",
        "params": [address, "latest"],
        "id": 1
    }
    response = requests.post(rpc_url, json=payload).json()
    return int(response["result"], 16)
