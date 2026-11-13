import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = {}
def add(name, kind, props, **extra):
    R[name] = {'Type': kind, 'Properties': props, **extra}
def ref(name): return {'Ref': name}
def att(name, key): return {'Fn::GetAtt': [name, key]}
def sub(s): return {'Fn::Sub': s}
def tags(): return [{'Key': 'Project', 'Value': 'SignalGraph'}]

add('Sources', 'AWS::S3::Bucket', {
    'BucketName': sub('signalgraph-sources-${AWS::AccountId}-${AWS::Region}'),
    'VersioningConfiguration': {'Status': 'Enabled'},
    'BucketEncryption': {'ServerSideEncryptionConfiguration': [{'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]},
    'PublicAccessBlockConfiguration': {k: True for k in ('BlockPublicAcls','BlockPublicPolicy','IgnorePublicAcls','RestrictPublicBuckets')},
    'OwnershipControls': {'Rules': [{'ObjectOwnership':'BucketOwnerEnforced'}]}, 'Tags': tags()
}, DeletionPolicy='Retain', UpdateReplacePolicy='Retain')
add('SourcesPolicy', 'AWS::S3::BucketPolicy', {'Bucket': ref('Sources'), 'PolicyDocument': {'Version':'2012-10-17','Statement':[{'Effect':'Deny','Principal':'*','Action':'s3:*','Resource':[att('Sources','Arn'),sub('${Sources.Arn}/*')],'Condition':{'Bool':{'aws:SecureTransport':'false'}}}]}})
add('Network', 'AWS::EC2::VPC', {'CidrBlock':'10.81.0.0/16','EnableDnsSupport':True,'EnableDnsHostnames':True,'Tags':tags()})
for i in (0,1):
    add('Subnet'+str(i), 'AWS::EC2::Subnet', {'VpcId':ref('Network'),'CidrBlock':f'10.81.{i+1}.0/24','AvailabilityZone':{'Fn::Select':[i,{'Fn::GetAZs':''}]},'MapPublicIpOnLaunch':False,'Tags':tags()})
add('Routes','AWS::EC2::RouteTable',{'VpcId':ref('Network'),'Tags':tags()})
for i in (0,1):
    add('RouteLink'+str(i),'AWS::EC2::SubnetRouteTableAssociation',{'SubnetId':ref('Subnet'+str(i)),'RouteTableId':ref('Routes')})
add('S3Endpoint','AWS::EC2::VPCEndpoint',{'VpcId':ref('Network'),'VpcEndpointType':'Gateway','ServiceName':sub('com.amazonaws.${AWS::Region}.s3'),'RouteTableIds':[ref('Routes')],'PolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':'*','Action':['s3:GetObject','s3:ListBucket'],'Resource':[att('Sources','Arn'),sub('${Sources.Arn}/*')]}]}})
add('GraphGroup','AWS::EC2::SecurityGroup',{'GroupDescription':'Private SignalGraph Neptune','VpcId':ref('Network'),'Tags':tags()})
add('ServiceGroup','AWS::EC2::SecurityGroup',{'GroupDescription':'SignalGraph query and import service','VpcId':ref('Network'),'Tags':tags()})
add('GraphIngress','AWS::EC2::SecurityGroupIngress',{'GroupId':ref('GraphGroup'),'IpProtocol':'tcp','FromPort':8182,'ToPort':8182,'SourceSecurityGroupId':ref('ServiceGroup')})
add('GraphSubnets','AWS::Neptune::DBSubnetGroup',{'DBSubnetGroupDescription':'SignalGraph private subnets','SubnetIds':[ref('Subnet0'),ref('Subnet1')],'Tags':tags()})
add('LoaderRole','AWS::IAM::Role',{'AssumeRolePolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'rds.amazonaws.com'},'Action':'sts:AssumeRole'}]},'Policies':[{'PolicyName':'ReadSignalGraphImport','PolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':'s3:ListBucket','Resource':att('Sources','Arn'),'Condition':{'StringLike':{'s3:prefix':['neptune/*']}}},{'Effect':'Allow','Action':'s3:GetObject','Resource':sub('${Sources.Arn}/neptune/*')}]}}],'Tags':tags()})
add('Graph','AWS::Neptune::DBCluster',{'DBClusterIdentifier':'signalgraph-main','DBSubnetGroupName':ref('GraphSubnets'),'VpcSecurityGroupIds':[ref('GraphGroup')],'StorageEncrypted':True,'IamAuthEnabled':True,'BackupRetentionPeriod':7,'DeletionProtection':True,'DBPort':8182,'ServerlessScalingConfiguration':{'MinCapacity':1,'MaxCapacity':2.5},'AssociatedRoles':[{'RoleArn':att('LoaderRole','Arn')}],'Tags':tags()},DeletionPolicy='Snapshot',UpdateReplacePolicy='Snapshot',DependsOn=['S3Endpoint','GraphIngress'])
add('Writer','AWS::Neptune::DBInstance',{'DBInstanceIdentifier':'signalgraph-main-writer','DBInstanceClass':'db.serverless','DBClusterIdentifier':ref('Graph'),'DBSubnetGroupName':ref('GraphSubnets'),'PubliclyAccessible':False,'Tags':tags()})
add('ServiceRole','AWS::IAM::Role',{'AssumeRolePolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'lambda.amazonaws.com'},'Action':'sts:AssumeRole'}]},'Policies':[{'PolicyName':'SignalGraphService','PolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':['logs:CreateLogStream','logs:PutLogEvents'],'Resource':sub('arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/signalgraph-graph-service:*')},{'Effect':'Allow','Action':['ec2:CreateNetworkInterface','ec2:DescribeNetworkInterfaces','ec2:DescribeSubnets','ec2:DeleteNetworkInterface','ec2:AssignPrivateIpAddresses','ec2:UnassignPrivateIpAddresses'],'Resource':'*'},{'Effect':'Allow','Action':['neptune-db:StartLoaderJob','neptune-db:GetLoaderJobStatus','neptune-db:ReadDataViaQuery','neptune-db:GetEngineStatus'],'Resource':sub('arn:${AWS::Partition}:neptune-db:${AWS::Region}:${AWS::AccountId}:${Graph.ClusterResourceId}/*')} ]}}],'Tags':tags()})
add('Logs','AWS::Logs::LogGroup',{'LogGroupName':'/aws/lambda/signalgraph-graph-service','RetentionInDays':30,'Tags':tags()})
add('Service','AWS::Lambda::Function',{'FunctionName':'signalgraph-graph-service','Description':'Private SignalGraph evidence graph import and bounded read queries','Runtime':'python3.13','Handler':'index.handler','Role':att('ServiceRole','Arn'),'MemorySize':256,'Timeout':120,'ReservedConcurrentExecutions':2,'Code':{'ZipFile':(HERE/'graph_service.py').read_text()},'Environment':{'Variables':{'GRAPH_ENDPOINT':att('Graph','Endpoint'),'SOURCE_BUCKET':ref('Sources'),'LOADER_ROLE':att('LoaderRole','Arn')}},'VpcConfig':{'SecurityGroupIds':[ref('ServiceGroup')],'SubnetIds':[ref('Subnet0'),ref('Subnet1')]},'Tags':tags()},DependsOn=['Logs','Writer'])
t={'AWSTemplateFormatVersion':'2010-09-09','Description':'SignalGraph private source archive and evidence graph','Resources':R,'Outputs':{'Bucket':{'Value':ref('Sources')},'Cluster':{'Value':ref('Graph')},'Endpoint':{'Value':att('Graph','Endpoint')},'Service':{'Value':ref('Service')},'Region':{'Value':ref('AWS::Region')}}}
(HERE/'signalgraph-stack.json').write_text(json.dumps(t,indent=2)+'\n')
print('Template:',len(R),'resources')
