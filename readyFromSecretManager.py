import boto3
import json

def retrieve_secret(secret_name, region_name):
    # Create a Secrets Manager client
    client = boto3.client('secretsmanager', region_name=region_name)
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        
        # Depending on whether the secret is a string or binary, one of these will be populated
        if 'SecretString' in response:
            secret = response['SecretString']
        else:
            secret = response['SecretBinary']
        
        return json.loads(secret)

    except Exception as e:
        print(f"Unable to retrieve secret: {e}")
        return None

if __name__ == "__main__":

    secret_name = "ALPFR/GLOBAL/APPS/DYNATRACE/CONNECT-INFO"
    region_name = "us-east-1"

    secret_value = retrieve_secret(secret_name, region_name)
    print(secret_value)
    
    if secret_value:
      print("Secret Retrived Successfull!")

      print(secret_value)
      print("APIURL ...: ", secret_value[0])
      print("TOKEN ....: ", secret_value[1])
    else:
      print("Failed to retrive secret.")
     
