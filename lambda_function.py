import boto3
import logging

# Initialize logging configuration
logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
rds_client = boto3.client('rds')

def lambda_handler(event, context):
    logger.info("Starting AWS FinOps Cost Optimization Sweep...")
    
    cleanup_unattached_ebs()
    cleanup_unused_elastic_ips()
    stop_non_prod_ec2_instances()
    stop_non_prod_rds_clusters()
    
    logger.info("FinOps Cost Optimization sweep completed successfully!")
    return {
        'statusCode': 200,
        'body': 'Optimization sweep completed.'
    }

def cleanup_unattached_ebs():
    logger.info("Scanning for unattached EBS volumes...")
    volumes = ec2_client.describe_volumes(
        Filters=[{'Name': 'status', 'Values': ['available']}]
    )
    
    for volume in volumes.get('Volumes', []):
        volume_id = volume['VolumeId']
        # Check if the volume is tagged to be skipped/kept
        skip_delete = False
        for tag in volume.get('Tags', []):
            if tag['Key'].lower() == 'keep' or tag['Key'].lower() == 'protection':
                skip_delete = True
                break
        
        if not skip_delete:
            logger.info(f"Deleting unattached volume: {volume_id} (Size: {volume['Size']}GB)")
            try:
                ec2_client.delete_volume(VolumeId=volume_id)
            except Exception as e:
                logger.error(f"Failed to delete volume {volume_id}: {str(e)}")
        else:
            logger.info(f"Skipping deletion for protected volume: {volume_id}")

def cleanup_unused_elastic_ips():
    logger.info("Scanning for unused Elastic IPs...")
    addresses = ec2_client.describe_addresses()
    for addr in addresses.get('Addresses', []):
        if 'AssociationId' not in addr:
            public_ip = addr['PublicIp']
            allocation_id = addr['AllocationId']
            logger.info(f"Releasing unassociated Elastic IP: {public_ip} (AllocationID: {allocation_id})")
            try:
                ec2_client.release_address(AllocationId=allocation_id)
            except Exception as e:
                logger.error(f"Failed to release Elastic IP {public_ip}: {str(e)}")

def stop_non_prod_ec2_instances():
    logger.info("Scanning for running non-production EC2 instances...")
    # Matches instances having Environment tag as dev/stage/test
    instances = ec2_client.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']},
            {'Name': 'tag:Environment', 'Values': ['dev', 'development', 'stage', 'staging', 'test']}
        ]
    )
    
    instances_to_stop = []
    for reservation in instances.get('Reservations', []):
        for instance in reservation.get('Instances', []):
            instances_to_stop.append(instance['InstanceId'])
            
    if instances_to_stop:
        logger.info(f"Stopping EC2 instances: {instances_to_stop}")
        try:
            ec2_client.stop_instances(InstanceIds=instances_to_stop)
        except Exception as e:
            logger.error(f"Failed to stop EC2 instances: {str(e)}")
    else:
        logger.info("No running non-production EC2 instances found.")

def stop_non_prod_rds_clusters():
    logger.info("Scanning for running non-production RDS database clusters...")
    clusters = rds_client.describe_db_clusters()
    
    for cluster in clusters.get('DBClusters', []):
        cluster_id = cluster['DBClusterIdentifier']
        status = cluster['Status']
        
        # Check environment tag
        is_non_prod = False
        arn = cluster['DBClusterArn']
        tags_response = rds_client.list_tags_for_resource(ResourceName=arn)
        for tag in tags_response.get('TagList', []):
            if tag['Key'].lower() == 'environment' and tag['Value'].lower() in ['dev', 'development', 'stage', 'staging', 'test']:
                is_non_prod = True
                break
                
        if is_non_prod and status == 'available':
            logger.info(f"Stopping RDS DB cluster: {cluster_id}")
            try:
                rds_client.stop_db_cluster(DBClusterIdentifier=cluster_id)
            except Exception as e:
                logger.error(f"Failed to stop RDS cluster {cluster_id}: {str(e)}")
