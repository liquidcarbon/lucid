# lucid/aws.py

__doc__ = """
AWS operations
"""
#-----------------------------------------------------------------------------
# Logging
#-----------------------------------------------------------------------------

import logging
_l = logging.getLogger(__name__)

#-----------------------------------------------------------------------------
# Imports & Options
#-----------------------------------------------------------------------------

# External imports
import base64
import boto3
import json
import os
import pandas as pd

# Lucid imports
from .util import me



#-----------------------------------------------------------------------------
# Globals & Constants
#-----------------------------------------------------------------------------


#-----------------------------------------------------------------------------
# AWS Services
#-----------------------------------------------------------------------------

class S3:
    """Class for S3 shenanigans.
    
    aws_params = dict(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        region_name='us-east-1',
    )
    """
    
    def __init__(self, **aws_params):
        self.client = boto3.client('s3', **aws_params)
        self.resource = boto3.resource('s3', **aws_params)
    
    def cat(self, s3url, encoding='utf-8'):
        """Prints (like Bash ``cat``) an S3 file."""
        s3url_parts = s3url.split('/', maxsplit=3)
        _bucket = s3url_parts[2]
        _key = s3url_parts[3]   

        o = self.client.get_object(Bucket=_bucket, Key=_key)
        # open the file object and read it into the variable filedata. 
        filedata = o['Body'].read()

        # file data will be a binary stream.  We have to decode it 
        contents = filedata.decode(encoding)
        print(contents)
        return None

    def ls(self, bucket, subfolder):
        """List files inside a subfolder."""
        o = self.resource.Bucket(bucket).objects
        return [f.key for f in o.filter(Prefix=subfolder).all()]

    def rm(self, bucket, subfolder, flags='rf'):
        """Recursively delete objects from a subfolder."""
        o = self.resource.Bucket(bucket).objects
        if flags == 'rf':
            o.filter(Prefix=subfolder).delete()
        return None


class Lambdas:
    """Class for finding and running Lambda functions.
    
    aws_params = dict(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        region_name='us-east-1',
    )
    """
    
    def __init__(self, **aws_params):
        self.client = boto3.client('lambda', **aws_params)
        
        # Paginator to retrieve all functions (otherwise 50 max)
        paginator = self.client.get_paginator('list_functions')
        page_iterator = paginator.paginate()

        # Retrieve all Lambda functions
        self.fnlist = []
        for page in page_iterator:
            self.fnlist.extend(page['Functions'])
    
    def find(self, s):
        self.results = []
        for fn in self.fnlist:
            if s in fn['FunctionName']:
                self.results.append(fn)
        print('  Result 1 out of {}:\n{}'.format(
            len(self.results), self.results[0])
        )
            
    def prep_invocation(self, i=0, **additional_params):
        _name = self.results[i]['FunctionName']
        _env = self.results[i]['Environment']['Variables']
        _payload = {
            'stateMachineArn': _env['DEFAULT_SFN_ARN'],
            'jobConfigUrl': _env['DEFAULT_CONFIG_FILE']
        }
        _payload.update(**additional_params)
        self.invocation = {
            'FunctionName': _name,
            'Payload': json.dumps(_payload).encode('utf-8'),
            'LogType': 'Tail',
        }
        return self.invocation
    
    def invoke(self, invocation_type='DryRun'):
        response = self.client.invoke(
            InvocationType = invocation_type,
            **self.invocation
        )
        print('Response:',response['ResponseMetadata']['HTTPStatusCode'])
        return response
