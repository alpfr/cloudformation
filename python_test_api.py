import base64
import datetime as dt
import json
import keyring
import pprint
import os
import pandas as pd
import requests

# Define authentication headers
usr = os.getenv('USERNAME')
print(usr)
psw = keyring.get_password('ad', usr)
auth_user = f'{usr}:{psw}'.encode()
headers = {
    "Authorization": base64.b64encode(auth_user)
}

# Define query parameters
params = {
    'start_ts': dt.datetime(2023,5,2).timestamp(),
    'stop_ts': dt.datetime(2023,5,3).timestamp(),
    'limit': 5
}

# Send the query
res = requests.get('http://127.0.0.1:5000/qry_wallet_transactions',
    params=params,
    headers=headers
)

# Extract the data into a dataframe
data = json.loads(res.json()['body'])
pd.Dataframe(data=data['data'],
    columns=data['columns']
)
