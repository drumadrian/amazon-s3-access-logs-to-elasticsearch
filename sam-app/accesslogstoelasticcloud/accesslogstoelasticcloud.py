
import json
import urllib.parse
import boto3
from elasticsearch import Elasticsearch
import requests
from datetime import datetime
from s3logparse import s3logparse
import os
import sys
from tempfile import NamedTemporaryFile
import traceback
import logging
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
patch_all()

######################################################################
# Notes:
######################################################################
# https://docs.aws.amazon.com/code-samples/latest/catalog/python-s3-get_object.py.html
# https://forums.aws.amazon.com/thread.jspa?threadID=221549
# https://stackoverflow.com/questions/32000934/python-print-a-variables-name-and-value
# https://pypi.org/project/s3-log-parse/
# https://www.geeksforgeeks.org/python-dictionary/
# https://stackoverflow.com/questions/44381249/treat-a-string-as-a-file-in-python
# https://github.com/elastic/elasticsearch-py
# https://docs.aws.amazon.com/lambda/latest/dg/running-lambda-code.html
# https://www.geeksforgeeks.org/python-interconversion-between-dictionary-and-bytes/
# https://stackoverflow.com/questions/2266646/how-to-disable-and-re-enable-console-logging-in-python/2267567#2267567


######################################################################
# Initialize boto3 client at global scope for connection reuse
######################################################################
print('Loading function')
client = boto3.client('ssm')
s3 = boto3.client('s3')


def lambda_handler(event, context):
    ######################################################################
    # Create and Configure Python logging 
    ######################################################################
    enable_logging = os.getenv('enable_logging')
    if enable_logging == 'True':
        enable_logging = True
        logging.Logger.disabled = False
    else: 
        enable_logging = False
        logging.Logger.disabled = True

    # log = logging.getLogger("accesslogstoelasticcloud")
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    # log.addHandler(handler)
    log.debug("Received event: " + json.dumps(event, indent=2))
    # print("Received event: " + json.dumps(event, indent=2))

    ######################################################################
    # Get all parameters containing credentials for this app
    #   If not -> user credentials from environment variables
    ######################################################################
    parent_stack_name = os.getenv('parent_stack_name')
    try:
        param_name = '/' + parent_stack_name + '/cloud_id'
        param_details = client.get_parameter(Name=param_name,WithDecryption=True)
        if 'Parameter' in param_details and len(param_details.get('Parameter')) > 0:
            parameter = param_details.get('Parameter')
            cloud_id = parameter.get('Value')
            log.info('cloud_id=' + cloud_id)

        param_name = '/' + parent_stack_name + '/http_auth_username'
        param_details = client.get_parameter(Name=param_name,WithDecryption=True)
        if 'Parameter' in param_details and len(param_details.get('Parameter')) > 0:
            parameter = param_details.get('Parameter')
            http_auth_username = parameter.get('Value')
            log.info('http_auth_username=' + http_auth_username)
        
        param_name = '/' + parent_stack_name + '/http_auth_password'
        param_details = client.get_parameter(Name=param_name,WithDecryption=True)
        if 'Parameter' in param_details and len(param_details.get('Parameter')) > 0:
            parameter = param_details.get('Parameter')
            http_auth_password = parameter.get('Value')
            log.info('http_auth_password=' + http_auth_password)

        param_name = '/' + parent_stack_name + '/index_name'
        param_details = client.get_parameter(Name=param_name,WithDecryption=True)
        if 'Parameter' in param_details and len(param_details.get('Parameter')) > 0:
            parameter = param_details.get('Parameter')
            index_name = parameter.get('Value')
            log.info('index_name=' + index_name)

    except:
        log.debug("Encountered an error loading credentials from SSM.")
        traceback.print_exc()
        cloud_id = os.getenv('cloud_id')
        http_auth_username = os.getenv('http_auth_username')
        http_auth_password = os.getenv('http_auth_password')
        index_name = os.getenv('index_name')
        

    ######################################################################
    # Get the object from the event and show its content type
    ######################################################################
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        log.info("CONTENT TYPE: " + response['ContentType'])
    except Exception as e:
        log.debug('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        log.debug(e)
        # print(e)
        # print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e
    
    StreamingBody=response['Body']
    access_log=StreamingBody.read()

    ######################################################################
    # Example Access Log:
    ######################################################################
    # access_log='2279185f7619a617e0a834c7f0660e4b09ea7f842f9d768d39109ee6e4cdf522 bucket [20/Dec/2019:06:36:32 +0000] 174.65.125.92 arn:aws:sts::696965430234:assumed-role/AWSReservedSSO_AdministratorAccess_563d3ebb7af9cd35/dev@company.com 6ED2206C36ABCD61 REST.GET.ACL object.mov "GET /bucket/object.mov?acl= HTTP/1.1" 200 - 550 - 277 - "-" "S3Console/0.4, aws-internal/3 aws-sdk-java/1.11.666 Linux/4.9.184-0.1.ac.235.83.329.metal1.x86_64 OpenJDK_64-Bit_Server_VM/25.232-b09 java/1.8.0_232 vendor/Oracle_Corporation" - eGkU7fkbpX9QOfaV1GDHSXQ9zVEokrE0KgIhdVMr63PbSCxWwZoEtr5GDbaDGr1/LFf9lTpiJ3U= SigV4 ECDHE-RSA-AES128-SHA AuthHeader s3-us-west-2.amazonaws.com TLSv1.2\n'
    log.info(f"access_log={access_log}\n")

    f = NamedTemporaryFile(mode='w+', delete=False)
    f.write(str(access_log))
    f.close()
    # with open(f.name, "r") as new_f:
    #     print(new_f.read())

    with open(f.name, "r") as fh:
        for log_entry in s3logparse.parse_log_lines(fh.readlines()):
            log.info(log_entry)

    os.unlink(f.name) # delete the file after usage

    ######################################################################
    # Start the X-Ray sub-segment
    ######################################################################
    subsegment = xray_recorder.begin_subsegment('accesslogstoelasticcloud - send data to ElasticCloud')
    subsegment.put_annotation('function', 'accesslogstoelasticcloud')
    xray_recorder.put_metadata("access_log", access_log)

    ##################################################################################################
    #Now put that data in ElasticCloud! 
    ##################################################################################################
    es = Elasticsearch(cloud_id=cloud_id, http_auth=(http_auth_username, http_auth_password))
    es.info()

    # create an index in elasticsearch, ignore status code 400 (index already exists)
    es.indices.create(index='accesslogstoelasticcloud', ignore=400)
    # {'acknowledged': True, 'shards_acknowledged': True, 'index': 'my-index'}
    # datetimes will be serialized
    # es.index(index="my-index", id=44, body={"any": "data44", "timestamp": datetime.now()})
    
    
    es_body={
    "bucket_owner": log_entry.bucket_owner,
    "bucket": log_entry.bucket,
    "timestamp": log_entry.timestamp,
    "remote_ip": log_entry.remote_ip,
    "requester": log_entry.requester,
    "request_id": log_entry.request_id,
    "operation": log_entry.operation,
    "s3_key": log_entry.s3_key,
    "request_uri": log_entry.request_uri,
    "status_code": log_entry.status_code,
    "error_code": log_entry.error_code,
    "bytes_sent": log_entry.bytes_sent,
    "object_size": log_entry.object_size,
    "total_time": log_entry.total_time,
    "turn_around_time": log_entry.turn_around_time,
    "referrer": log_entry.referrer,
    "user_agent": log_entry.user_agent,
    "version_id": log_entry.version_id
    }

    es.index(index=index_name, body=es_body)

    ######################################################################
    # End the X-Ray sub-segment
    ######################################################################
    xray_recorder.end_subsegment()

