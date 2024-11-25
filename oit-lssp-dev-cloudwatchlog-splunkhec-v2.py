mport boto3
import os
import json
import requests
import logging
from datetime import datetime, timedelta

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set logger to debug mode

# Environment variables for region, Splunk HEC, and CloudWatch Log Group
REGION = 'us-gov-west-1'  # GovCloud region
LOG_GROUP_NAME = os.getenv('LOG_GROUP_NAME', '/aws/lambda/UAT_L1_adhoc_invoker')
SPLUNK_HEC_URL = os.getenv('SPLUNK_HEC_URL', 'https://173.69.170.80:8088/services/collector/event')
#SPLUNK_HEC_URL = os.getenv('SPLUNK_HEC_URL', 'https://173.69.170.80:8088/services/collector/event?auto_extract_timestamp=true')
SPLUNK_HEC_TOKEN = os.getenv('SPLUNK_HEC_TOKEN', '4d20909d-8de0-4e8d-8932-54b3ed8647cc')
SPLUNK_INDEX = os.getenv('SPLUNK_INDEX', 'splunk_demo')
SPLUNK_HEC_CHANNEL = os.getenv('SPLUNK_HEC_CHANNEL', '18fafdc0-bc0a-3845-a038-4deef382c6d2')

# Initialize the CloudWatch Logs client
cloudwatch_logs = boto3.client('logs', region_name=REGION)

def lambda_handler(event, context):
    logger.debug("Starting Lambda handler execution.")
    logger.debug(f"Using Log Group: {LOG_GROUP_NAME}")

    try:
        # Set up time range for log retrieval (e.g., last 5 minutes)
        start_time = int((datetime.now() - timedelta(minutes=30)).timestamp() * 1000)
        end_time = int(datetime.now().timestamp() * 1000)
        logger.debug(f"Retrieving logs from CloudWatch between {start_time} and {end_time}")

        # Describe log streams in the CloudWatch Log Group
        log_streams = cloudwatch_logs.describe_log_streams(
            logGroupName=LOG_GROUP_NAME,
            orderBy='LastEventTime',
            descending=True
        )['logStreams']

        logger.debug(f"Retrieved {len(log_streams)} log streams.")

        splunk_events = []  # To accumulate Splunk events

        for stream in log_streams:
            stream_name = stream['logStreamName']
            logger.debug(f"Processing log stream: {stream_name}")

            # Get log events for the stream
            log_events = cloudwatch_logs.get_log_events(
                logGroupName=LOG_GROUP_NAME,
                logStreamName=stream_name,
                startTime=start_time,
                endTime=end_time
            )['events']

            print(f'Print the log_events ...: {log_events}')

            if log_events:
                logger.debug(f"Retrieved {len(log_events)} events from stream {stream_name}")
                for event in log_events:
                    # Create a Splunk event from the log message
                    splunk_event = create_splunk_event(event)
                    splunk_events.append(splunk_event)

            # Send the logs to Splunk in batches (optional)
            if len(splunk_events) > 0:
                logger.debug(f"Sending {len(splunk_events)} events to Splunk.")
                send_to_splunk(splunk_events)
                splunk_events = []  # Clear the list after sending

        logger.debug("Lambda execution completed successfully.")
        return {
            'statusCode': 200,
            'body': 'Logs successfully forwarded to Splunk HEC.'
        }

    except Exception as e:
        logger.error(f"Error processing CloudWatch Logs: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': f"Error: {str(e)}"
        }

def create_splunk_event(log_event):
    """Create a Splunk event from a CloudWatch log event."""
    try:
        # Splunk event structure
        splunk_event = {
            "time": log_event['timestamp'] / 1000,  # Convert from ms to seconds
            "host": LOG_GROUP_NAME,
            "source": LOG_GROUP_NAME,
            "sourcetype": "aws:cloudwatch",
            #"index": SPLUNK_INDEX,
            "event": log_event['message']
        }
        logger.debug(f"Created Splunk event: {splunk_event}")
        return splunk_event
    except Exception as e:
        logger.error(f"Failed to create Splunk event: {str(e)}", exc_info=True)
        return None

def send_to_splunk(events):
    """Send a batch of events to Splunk HEC."""
    try:
        logger.debug(f"Preparing to send {len(events)} events to Splunk HEC.")

        # HTTP headers for Splunk HEC
        headers = {
            "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}",
            "X-Splunk-Request-Channel": SPLUNK_HEC_CHANNEL,
            "Content-Type": "application/json"
        }

        # Send logs to the Splunk HEC endpoint
        response = requests.post(SPLUNK_HEC_URL, headers=headers, data=json.dumps({"event": events}), verify=False)

        if response.status_code == 200:
            logger.debug(f"Successfully sent {len(events)} events to Splunk.")
        else:
            logger.error(f"Failed to send data to Splunk. Status: {response.status_code}, Response: {response.text}")

    except Exception as e:
        logger.error(f"Error sending data to Splunk: {str(e)}", exc_info=True)

# For local testing (if needed)
if __name__ == "__main__":
    lambda_handler(None, None)
