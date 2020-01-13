import json
import boto3
import requests
import os

def empty_delete_buckets(bucket_name):
    """
    Empties and deletes the bucket
    :param bucket_name:
    :param region:
    :return:
    """
    print ("trying to delete the bucket {0}".format(bucket_name))
    s3_client = boto3.client('s3')
    s3 = boto3.resource('s3')

    try:
        bucket = s3.Bucket(bucket_name).load()
    except:
        print ("bucket {0} does not exist".format(bucket_name))
        return
    # Check if versioning is enabled
    response = s3_client.get_bucket_versioning(Bucket=bucket_name)
    status = response.get('Status','')
    if status == 'Enabled':
        response = s3_client.put_bucket_versioning(Bucket=bucket_name,
                                                   VersioningConfiguration={'Status': 'Suspended'})
    paginator = s3_client.get_paginator('list_object_versions')
    page_iterator = paginator.paginate(
        Bucket=bucket_name
    )

    for page in page_iterator:
        print (page)
        if 'DeleteMarkers' in page:
            delete_markers = page['DeleteMarkers']
            if delete_markers is not None:
                for delete_marker in delete_markers:
                    key = delete_marker['Key']
                    versionId = delete_marker['VersionId']
                    s3_client.delete_object(Bucket=bucket_name, Key=key, VersionId=versionId)
        if 'Versions' in page and page['Versions'] is not None:
            versions = page['Versions']
            for version in versions:
                print (version)
                key = version['Key']
                versionId = version['VersionId']
                s3_client.delete_object(Bucket=bucket_name, Key=key, VersionId=versionId)
    object_paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = object_paginator.paginate(
        Bucket=bucket_name
    )
    for page in page_iterator:
        if 'Contents' in page:
            for content in page['Contents']:
                key = content['Key']
                s3_client.delete_object(Bucket=bucket_name, Key=content['Key'])
    #UNCOMMENT THE LINE BELOW TO MAKE LAMBDA DELETE THE BUCKET.  
    # THIS WILL CAUSE AN FAILURE SINCE CLOUDFORMATION ALSO TRIES TO DELETE THE BUCKET
    #s3_client.delete_bucket(Bucket=bucket_name)
    #print "Successfully deleted the bucket {0}".format(bucket_name)
    print ("Successfully emptied the bucket {0}".format(bucket_name))



def lambda_handler(event, context):
    try:
        # bucket = event['ResourceProperties']['BucketName']
        bucket = os.getenv('s3_bucket_name')
        if event['RequestType'] == 'Delete':
            empty_delete_buckets(bucket)
        sendResponseCfn(event, context, "SUCCESS")
    except Exception as e:
        print(e)
        sendResponseCfn(event, context, "FAILED")

def sendResponseCfn(event, context, responseStatus):
    response_body = {'Status': responseStatus,
                    'Reason': 'Log stream name: ' + context.log_stream_name,
                    'PhysicalResourceId': context.log_stream_name,
                    'StackId': event['StackId'],
                    'RequestId': event['RequestId'],
                    'LogicalResourceId': event['LogicalResourceId'],
                    'Data': json.loads("{}")}
    requests.put(event['ResponseURL'], data=json.dumps(response_body))

