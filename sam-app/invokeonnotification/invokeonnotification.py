import os
import io
import sys
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
    # log.setLevel(logging.DEBUG)
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    # log.addHandler(handler)
    enable_logging = os.getenv('enable_logging')
    if enable_logging == 'True':
        enable_logging = True
        logging.Logger.disabled = False
    else: 
        enable_logging = False
        logging.Logger.disabled = True

    try:
        log.info("Received event: " + json.dumps(event, indent=2))
        lambda_client = boto3.client('lambda')
        labmdafunction1 = os.getenv('labmdafunction1')
        labmdafunction2 = os.getenv('labmdafunction2')
        AWS_XRAY_TRACING_NAME = os.getenv('AWS_XRAY_TRACING_NAME')
    except:
        log.debug("failed to initialize function data!")


    ######################################################################
    # Start X-Ray segment
    # https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-python-segment.html
    # https://docs.aws.amazon.com/xray-sdk-for-python/latest/reference/basic.html
    # ONLY SUBSEGMENTS IN AWS LAMBDA FUNCTIONS
    # SUBSEGMENTS CANNOT SET THE USER
    ######################################################################
    # segment = xray_recorder.begin_segment('invokeonnotification')
    # document = xray_recorder.current_segment()
    # segment = xray_recorder.current_segment()


    ######################################################################
    # Invoke Labmda functions within X-Ray sub-segments
    ######################################################################
    # log.debug("hello stdout world")
    subsegment = xray_recorder.begin_subsegment('labmdafunction1')
    subsegment.put_annotation('function_name', labmdafunction1)
    now = datetime.now() # current date and time
    time_now = now.strftime("%H:%M:%S.%f")
    subsegment.put_annotation("Version", "2.0")
    subsegment.put_annotation("Developer", "Adrian")
    subsegment.put_annotation("lambdafunction", "invokeonnotification")
    subsegment.put_metadata("function", __name__)
    subsegment.put_metadata("enable_logging", enable_logging)
    subsegment.put_metadata("system time H:M:S.milliseconds", time_now)
    # subsegment.set_user("invokeonnotification")

    
    # f = io.BytesIO(b'test')
    # f.read()

    log.info((str(type(event))))
    
    # using encode() + dumps() to convert to bytes 
    res_bytes = json.dumps(event).encode('utf-8') 
    
    # printing type and binary dict  
    log.info("The type after conversion to bytes is : " + str(type(res_bytes))) 
    log.info("The value after conversion to bytes is : " + str(res_bytes)) 


    ######################################################################
    # Start the X-Ray sub-segment
    ######################################################################
    subsegment = xray_recorder.begin_subsegment('labmdafunction1')
    subsegment.put_annotation('function_arn', labmdafunction1)
    log.info("Invoking labmdafunction1")    
    response1 = lambda_client.invoke(
                                    FunctionName=labmdafunction1,
                                    InvocationType='Event',
                                    Payload=res_bytes
                                    )  
    xray_recorder.put_metadata("response1", response1)
    xray_recorder.end_subsegment()

    ######################################################################
    # Start the X-Ray sub-segment
    ######################################################################
    subsegment = xray_recorder.begin_subsegment('labmdafunction2')
    subsegment.put_annotation('function_arn', labmdafunction2)
    log.info("Invoking labmdafunction2")
    response2 = lambda_client.invoke(
                                    FunctionName=labmdafunction2,
                                    InvocationType='Event',
                                    Payload=res_bytes
                                    )  

    xray_recorder.put_metadata("response2", response2)
    xray_recorder.end_subsegment()





