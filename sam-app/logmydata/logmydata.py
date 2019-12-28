
import json
import urllib.parse
import boto3

from elasticsearch import Elasticsearch
import requests
from datetime import datetime

from s3logparse import s3logparse

import os
from tempfile import NamedTemporaryFile

import traceback
# import os, traceback, json, boto3

from aws_xray_sdk.core import patch_all
patch_all()

# Notes:
# https://docs.aws.amazon.com/code-samples/latest/catalog/python-s3-get_object.py.html
# https://forums.aws.amazon.com/thread.jspa?threadID=221549
# https://stackoverflow.com/questions/32000934/python-print-a-variables-name-and-value
# https://pypi.org/project/s3-log-parse/
# https://www.geeksforgeeks.org/python-dictionary/
# https://stackoverflow.com/questions/44381249/treat-a-string-as-a-file-in-python
# https://github.com/elastic/elasticsearch-py
# https://docs.aws.amazon.com/lambda/latest/dg/running-lambda-code.html


print('Loading function')


# Initialize boto3 client at global scope for connection reuse
client = boto3.client('ssm')
s3 = boto3.client('s3')

cloud_id_var = os.getenv('cloud_id')
http_auth_username = os.getenv('http_auth_username')
http_auth_password = os.getenv('http_auth_password')
index_name = os.getenv('index_name')


def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))


    try:
        # Get all parameters for this app is not set using environment variables

        param_details = client.get_parameter(Name='/logmydata/cloud_id',WithDecryption=True)
        if 'Parameter' in param_details and len(param_details.get('Parameter')) > 0 and cloud_id_var is not "-":
            for param in param_details.get('Parameter'):
                cloud_id_var = param.get('Value')

        param_details = client.get_parameter(Name='/logmydata/http_auth_username',WithDecryption=True)
        if 'Parameter' in param_details and len(param_details.get('Parameter')) > 0 and http_auth_username is not "-":
            for param in param_details.get('Parameter'):
                http_auth_username = param.get('Value')

        param_details = client.get_parameter(Name='/logmydata/http_auth_password',WithDecryption=True)
        if 'Parameter' in param_details and len(param_details.get('Parameter')) > 0 and http_auth_password is not "-":
            for param in param_details.get('Parameter'):
                http_auth_password = param.get('Value')

        param_details = client.get_parameter(Name='/logmydata/index_name',WithDecryption=True)
        if 'Parameter' in param_details and len(param_details.get('Parameter')) > 0 and index_name is not "-":
            for param in param_details.get('Parameter'):
                index_name = param.get('Value')

    except:
        print("Encountered an error loading credentials from SSM.")
        traceback.print_exc()


    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        print("CONTENT TYPE: " + response['ContentType'])
        # return response['ContentType']
    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e
    
    StreamingBody=response['Body']
    access_log=StreamingBody.read()

    # Example Log:
    # access_log='2279185f7619a617e0a834c7f0660e4b09ea7f842f9d768d39109ee6e4cdf522 bucket [20/Dec/2019:06:36:32 +0000] 174.65.125.92 arn:aws:sts::696965430582:assumed-role/AWSReservedSSO_AdministratorAccess_563d3ebb7af9cd35/dev@company.com 6ED2206C36ABCD61 REST.GET.ACL object.mov "GET /bucket/object.mov?acl= HTTP/1.1" 200 - 550 - 277 - "-" "S3Console/0.4, aws-internal/3 aws-sdk-java/1.11.666 Linux/4.9.184-0.1.ac.235.83.329.metal1.x86_64 OpenJDK_64-Bit_Server_VM/25.232-b09 java/1.8.0_232 vendor/Oracle_Corporation" - eGkU7fkbpX9QOfaV1GDHSXQ9zVEokrE0KgIhdVMr63PbSCxWwZoEtr5GDbaDGr1/LFf9lTpiJ3U= SigV4 ECDHE-RSA-AES128-SHA AuthHeader s3-us-west-2.amazonaws.com TLSv1.2\n'

    print(f"access_log={access_log}\n")

    f = NamedTemporaryFile(mode='w+', delete=False)
    f.write(str(access_log))
    f.close()
    # with open(f.name, "r") as new_f:
    #     print(new_f.read())


    with open(f.name, "r") as fh:
        for log_entry in s3logparse.parse_log_lines(fh.readlines()):
            print(log_entry)

    os.unlink(f.name) # delete the file after usage


##################################################################################################
    #Now put that data in ElasticCloud! 
##################################################################################################


    es = Elasticsearch(cloud_id=cloud_id_var, http_auth=(http_auth_username,http_auth_password))
    es.info()

    # result = es.search(index="sw", doc_type="people", body=search_definition)
    # print(json.dumps(result, indent=4))


    # create an index in elasticsearch, ignore status code 400 (index already exists)
    es.indices.create(index='access-logs', ignore=400)
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







