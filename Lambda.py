import boto3
import os
import tempfile

# AWS Clients
s3_client = boto3.client('s3')
eb_client = boto3.client('elasticbeanstalk')

# Configuration
APPLICATION_NAME = "YourElasticBeanstalkAppName"     # Change this
ENVIRONMENT_NAME = "YourElasticBeanstalkEnvName"     # Change this

def lambda_handler(event, context):
    # Get file info from the S3 event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    s3_key = event['Records'][0]['s3']['object']['key']
    
    if not s3_key.endswith('.war'):
        print("Not a WAR file. Skipping.")
        return
    
    # Download the .war file to Lambda's /tmp directory
    tmp_file_path = os.path.join(tempfile.gettempdir(), os.path.basename(s3_key))
    s3_client.download_file(bucket_name, s3_key, tmp_file_path)
    print(f"Downloaded {s3_key} from {bucket_name} to {tmp_file_path}")
    
    # Upload the file to Elastic Beanstalk's S3 bucket for app versions
    eb_bucket = f"elasticbeanstalk-{os.environ['AWS_REGION']}-{boto3.client('sts').get_caller_identity()['Account']}"
    eb_key = os.path.basename(s3_key)
    s3_client.upload_file(tmp_file_path, eb_bucket, eb_key)
    print(f"Uploaded WAR to {eb_bucket}/{eb_key} for EB deployment")
    
    # Create a new Elastic Beanstalk application version
    version_label = f"version-{int(context.aws_request_id[:8], 16)}"
    eb_client.create_application_version(
        ApplicationName=APPLICATION_NAME,
        VersionLabel=version_label,
        SourceBundle={
            'S3Bucket': eb_bucket,
            'S3Key': eb_key
        },
        Process=True
    )
    print(f"Created new EB app version: {version_label}")
    
    # Update environment to use the new version
    eb_client.update_environment(
        EnvironmentName=ENVIRONMENT_NAME,
        VersionLabel=version_label
    )
    print(f"Updated environment {ENVIRONMENT_NAME} to version {version_label}")

