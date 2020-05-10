import os
import json
import boto3
import logging
from datetime import datetime
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
patch_all()



# Initialize boto3 client at global scope for connection reuse
print('Loading function')


def lambda_handler(event, context):

    ######################################################################
    # Create, Add, and Configure Python logging handler
    # https://stackoverflow.com/questions/2266646/how-to-disable-and-re-enable-console-logging-in-python/2267567#2267567
    ######################################################################
    log = logging.getLogger("invokeonnotification-Logger")
    log.setLevel(logging.DEBUG)
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    # log.addHandler(handler)
    enable_logging = os.getenv('enable_logging')
    if enable_logging == 'True':
        enable_logging = True
        logger.disabled = False
    else: 
        enable_logging = False
        logger.disabled = True

    try:
        print("Received event: " + json.dumps(event, indent=2))
        lambda_client = boto3.client('lambda')
        labmdafunction1 = os.getenv('labmdafunction1')
        labmdafunction2 = os.getenv('labmdafunction2')
        AWS_XRAY_TRACING_NAME = os.getenv('AWS_XRAY_TRACING_NAME')
    except:
        print("failed to initialize function data!")


    ######################################################################
    # Start X-Ray segment
    # https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-python-segment.html
    ######################################################################
    segment = xray_recorder.begin_segment('invokeonnotification')
    now = datetime.now() # current date and time
    time_now = now.strftime("%H:%M:%S.%f")
    xray_recorder.put_annotation("Version", "2.0")
    xray_recorder.put_annotation("Developer", "Adrian")
    xray_recorder.put_annotation("lambdafunction", "invokeonnotification")
    xray_recorder.put_metadata("function", __name__)
    xray_recorder.put_metadata("enable_logging", enable_logging)
    xray_recorder.put_metadata("system time H:M:S.milliseconds", time_now)
    document = xray_recorder.current_segment()
    document.set_user("invokeonnotification")
    document = xray_recorder.current_segment()


    ######################################################################
    # Invoke Labmda functions within X-Ray sub-segments
    ######################################################################
    # log.debug("hello stdout world")
    log.info("Invoking labmdafunction1")
    subsegment = xray_recorder.begin_subsegment('labmdafunction1')
    subsegment.put_annotation('function name', labmdafunction1)
    response1 = lambda_client.invoke(
                                    FunctionName=labmdafunction1,
                                    InvocationType='Event',
                                    Payload=event
                                    )  
    xray_recorder.put_metadata("response1", response1)
    xray_recorder.end_subsegment()


    log.info("Invoking labmdafunction2")
    subsegment = xray_recorder.begin_subsegment('labmdafunction2')
    subsegment.put_annotation('function name', labmdafunction2)
    response2 = lambda_client.invoke(
                                    FunctionName=labmdafunction2,
                                    InvocationType='Event',
                                    Payload=event
                                    )  

    xray_recorder.put_metadata("response2", response2)
    xray_recorder.end_subsegment()


    ######################################################################
    # Close the X-Ray segment
    ######################################################################
    xray_recorder.end_segment()



