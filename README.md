# AWS FinOps Cost Optimizer Bot

An automated Python-based AWS Lambda application designed to optimize AWS resource billing by pruning orphaned resources and shutting down non-production environments outside working hours.

## 💰 Key Optimizations

1. **Delete Orphaned EBS Volumes**: Automatically detects and deletes EBS volumes in the `available` state (unattached) to eliminate storage fees. Includes a safety guard to skip volumes with a `Keep` or `Protection` tag.
2. **Release Unused Elastic IPs**: Releases Elastic IPs that are allocated but not associated with any EC2 instance to prevent AWS hourly idle fees.
3. **EC2 Shutdown Scheduler**: Automatically stops running EC2 instances tagged as `dev`, `stage`, or `test` environments during non-working hours.
4. **RDS Shutdown Scheduler**: Automatically stops active multi-az RDS databases and Aurora DB clusters tagged with non-production environment labels.

## 📦 Directory Structure

```
.
├── lambda_function.py  # Core Boto3 cleanup logic and entry point
├── requirements.txt    # Lambda package dependencies
├── .gitignore          # File exclusion configuration
└── README.md           # Bot documentation page
```

## ⚙️ Deployment Guide

### Deploying to AWS Lambda

1. **Package the Lambda function**:
   ```bash
   # Install dependencies locally in a package folder
   pip install -r requirements.txt -t .
   # Compress files into a deployable zip archive
   zip -r cost-optimizer.zip .
   ```

2. **Create AWS Lambda Function**:
   - Runtime: `Python 3.10` or higher.
   - Timeout: `5 minutes` (to support AWS API scan ranges).
   - Execution Role: Attach an IAM policy granting permissions to read and write EC2/RDS resource states:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "ec2:DescribeVolumes",
             "ec2:DeleteVolume",
             "ec2:DescribeAddresses",
             "ec2:ReleaseAddress",
             "ec2:DescribeInstances",
             "ec2:StopInstances",
             "rds:DescribeDBClusters",
             "rds:StopDBCluster",
             "rds:ListTagsForResource"
           ],
           "Resource": "*"
         }
       ]
     }
     ```

3. **Schedule Execution (EventBridge Cron)**:
   - Create an **Amazon EventBridge Rule** with a Cron trigger to invoke the Lambda function automatically every day at 7:00 PM:
     `cron(0 19 * * ? *)`

## 📜 License

This project is licensed under the MIT License.
