import boto3
import json

def get_secret(secret_name, region_name):
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)

    try:
        # Attempt to retrieve the secret value
        response = client.get_secret_value(SecretId=secret_name)

    except Exception as e:
        # Handle exceptions
        print(f"Error retrieving secret: {str(e)}")
        return None

    # Decrypts secret using the associated KMS CMK.
    if 'SecretString' in response:
        secret = response['SecretString']
        return json.loads(secret)
    else:
        secret = json.loads(response['SecretBinary'])
        return secret

if __name__ == "__main__":
    secret_name = "ALPFR/GLOBAL/APPS/DYNATRACE/CONNECT-INFO"  # replace with your secret's name
    region_name = "us-east-1"  # replace with your AWS region

    secret = get_secret(secret_name, region_name)
    if secret:
        print("Secret Retrieved Successfully!")
        
        # Output the value of "APIURL" and "TOKEN" if they exist in the secret
        for key in ["APIURL", "TOKEN"]:
            if key in secret:
                print(f"{key}: {secret[key]}")
            else:
                print(f"The key '{key}' is not found in the secret.")
    else:
        print("Failed to retrieve secret.")

