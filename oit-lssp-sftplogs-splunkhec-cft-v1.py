import boto3
import os
import json
from datetime import datetime, timedelta
import requests
import logging

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set to DEBUG level

# Set variables
AWS_REGION = "us-gov-west-1"
SPLUNK_HEC_URL = "https://dzsplunkhec.sec.gov:8088/services/collector/event?auto_extract_timestamp=true"
HEC_CHANNEL = "18fafdc0-bc0a-3845-a038-4deef382c6d2"
HEC_TOKEN = "67892b54-ba53-4187-9ecb-8bf3dc54a2e9"
INDEX = "splunk_demo"

def get_lambda_nat_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except requests.RequestException as e:
        logger.error(f"Error getting NAT IP: {str(e)}")
        return 'Unknown'

LAMBDA_NAT_IP = get_lambda_nat_ip()
logger.debug(f"Lambda NAT IP: {LAMBDA_NAT_IP}")

def lambda_handler(event, context):
    logs_client = boto3.client('logs', region_name=AWS_REGION)
    log_group_name = os.environ.get('LOG_GROUP_NAME', '/aws/transfer/your-server-id')
    
    logger.debug(f"Processing logs from group: {log_group_name}")
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)
    
    start_time_ms = int(start_time.timestamp() * 1000)
    end_time_ms = int(end_time.timestamp() * 1000)
    
    try:
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time_ms,
            endTime=end_time_ms,
            limit=100
        )
        
        log_events = response['events']
        logger.debug(f"Retrieved {len(log_events)} log events")
        
        processed_events = []
        
        for event in log_events:
            try:
                message = json.loads(event['message'])
                if message['type'] == 'StepStarted':
                    details = message['details']
                    processed_event = {
                        'time': event['timestamp'],
                        'source': 'aws:sftp',
                        'sourcetype': 'aws:sftp:transfer',
                        'index': INDEX,
                        'event': {
                            'type': message['type'],
                            'stepType': details['stepType'],
                            'stepName': details['stepName'],
                            'workflowId': details['workflowId'],
                            'executionId': details['executionId'],
                            'serverId': details['transferDetails']['serverId'],
                            'username': details['transferDetails']['username'],
                            'sessionId': details['transferDetails']['sessionId'],
                            'fileLocation': {
                                'backingStore': details['input']['fileLocation']['backingStore'],
                                'bucket': details['input']['fileLocation']['bucket'],
                                'key': details['input']['fileLocation']['key'],
                                'etag': details['input']['fileLocation']['etag']
                            },
                            'lambda_nat_ip': LAMBDA_NAT_IP
                        }
                    }
                    processed_events.append(processed_event)
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON for event: {event['message']}")
            except KeyError as e:
                logger.error(f"KeyError processing event: {str(e)}")
        
        logger.debug(f"Processed {len(processed_events)} events")
        
        if processed_events:
            send_to_splunk(processed_events)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f"Retrieved, processed, and sent {len(processed_events)} log events to Splunk",
                'lambda_nat_ip': LAMBDA_NAT_IP,
                'events': processed_events
            })
        }
    
    except Exception as e:
        logger.error(f"Error retrieving or processing log events: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f"Error retrieving or processing log events: {str(e)}",
                'lambda_nat_ip': LAMBDA_NAT_IP
            })
        }

def send_to_splunk(events):
    headers = {
        'Authorization': f'Splunk {HEC_TOKEN}',
        'Content-Type': 'application/json',
        'X-Splunk-Request-Channel': HEC_CHANNEL
    }
    
    payload = {
        'channel': HEC_CHANNEL,
        'events': events
    }
    
    try:
        response = requests.post(SPLUNK_HEC_URL, headers=headers, json=payload, verify=False)
        response.raise_for_status()
        logger.debug(f"Successfully sent {len(events)} events to Splunk.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending events to Splunk: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            logger.error(f"Response content: {e.response.text}")
