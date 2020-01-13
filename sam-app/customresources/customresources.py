import json
import boto3
import requests
import os


def create_resources(parent_stack_name):

    print ("trying to Create resources for {0}".format(parent_stack_name))
    ssm_client = boto3.client('ssm')
    ParameterStoreEncryptionKey = os.getenv('ParameterStoreEncryptionKey')
    print ("Now adding 4 secure parameters using KMS key")

    response = ssm_client.put_parameter(
        Name='/' + parent_stack_name + '/cloud_id',
        Description='secure parameter using KMS key',
        Value='+',
        Type='SecureString',
        KeyId=ParameterStoreEncryptionKey,
        Overwrite=False,
        Tags=[
            {
                'Key': 'Created by',
                'Value': 'Custom Cloud Formation resource'
            },
        ],
        Tier='Intelligent-Tiering'
    )
    response = ssm_client.put_parameter(
        Name='/' + parent_stack_name + '/http_auth_username',
        Description='secure parameter using KMS key',
        Value='+',
        Type='SecureString',
        KeyId=ParameterStoreEncryptionKey,
        Overwrite=False,
        Tags=[
            {
                'Key': 'Created by',
                'Value': 'Custom Cloud Formation resource'
            },
        ],
        Tier='Intelligent-Tiering'
    )
    response = ssm_client.put_parameter(
        Name='/' + parent_stack_name + '/http_auth_password',
        Description='secure parameter using KMS key',
        Value='+',
        Type='SecureString',
        KeyId=ParameterStoreEncryptionKey,
        Overwrite=False,
        Tags=[
            {
                'Key': 'Created by',
                'Value': 'Custom Cloud Formation resource'
            },
        ],
        Tier='Intelligent-Tiering'
    )
    response = ssm_client.put_parameter(
        Name='/' + parent_stack_name + '/index_name',
        Description='secure parameter using KMS key',
        Value='+',
        Type='SecureString',
        KeyId=ParameterStoreEncryptionKey,
        Overwrite=False,
        Tags=[
            {
                'Key': 'Created by',
                'Value': 'Custom Cloud Formation resource'
            },
        ],
        Tier='Intelligent-Tiering'
    )


def delete_resources(parent_stack_name):

    print ("trying to Delete resources for {0}".format(parent_stack_name))
    ssm_client = boto3.client('ssm')
    print ("Now Deleting 4 secure parameters ")
    response = ssm_client.delete_parameters(
        Names=[
            '/' + parent_stack_name + '/cloud_id',
            '/' + parent_stack_name + '/http_auth_username',
            '/' + parent_stack_name + '/http_auth_password',
            '/' + parent_stack_name + '/index_name'
        ]
    )


def lambda_handler(event, context):
    try:

        parent_stack_name = os.getenv('parent_stack_name')
        if event['RequestType'] == 'Create':
            create_resources(parent_stack_name)

        if event['RequestType'] == 'Delete':
            delete_resources(parent_stack_name)

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

