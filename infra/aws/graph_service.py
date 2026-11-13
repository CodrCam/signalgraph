import json
import os

import boto3
from botocore.config import Config


def handler(event, context):
    client = boto3.client(
        'neptunedata', endpoint_url='https://' + os.environ['GRAPH_ENDPOINT'] + ':8182',
        config=Config(connect_timeout=10, read_timeout=90, retries={'max_attempts': 2}))
    action = event.get('action', 'counts')
    if action == 'load':
        result = client.start_loader_job(
            source='s3://' + os.environ['SOURCE_BUCKET'] + '/neptune/2026-11-13/',
            format='csv', s3BucketRegion=os.environ['AWS_REGION'],
            iamRoleArn=os.environ['LOADER_ROLE'], mode='AUTO', failOnError=True,
            parallelism='LOW', updateSingleCardinalityProperties=True,
            queueRequest=True)
    elif action == 'status':
        result = client.get_loader_job_status(loadId=event['load_id'], details=True, errors=True)
    elif action == 'health':
        result = client.get_engine_status()
    elif action == 'counts':
        result = {
            'vertices': client.execute_open_cypher_query(openCypherQuery='MATCH (n) RETURN count(n) AS count')['results'],
            'edges': client.execute_open_cypher_query(openCypherQuery='MATCH ()-[r]->() RETURN count(r) AS count')['results'],
            'labels': client.execute_open_cypher_query(openCypherQuery='MATCH (n) RETURN labels(n) AS labels, count(*) AS count ORDER BY count DESC')['results']}
    elif action == 'connections':
        entity_id = event.get('entity_id', '')
        if not isinstance(entity_id, str) or not 1 <= len(entity_id) <= 160:
            raise ValueError('An entity ID is required')
        result = client.execute_open_cypher_query(
            openCypherQuery='MATCH (n)-[r]-(m) WHERE id(n) = $entity_id RETURN id(n) AS root, properties(n) AS person, type(r) AS relationship, properties(r) AS evidence, id(m) AS connected_id, properties(m) AS connected LIMIT 100',
            parameters=json.dumps({'entity_id': entity_id}))
    else:
        raise ValueError('Unknown action')
    result.pop('ResponseMetadata', None)
    return json.loads(json.dumps(result, default=str))
