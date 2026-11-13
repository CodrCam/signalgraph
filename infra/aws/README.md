# Source archive and graph

This optional AWS backend stores source documents in a private versioned S3 bucket and reviewed relationships in Amazon Neptune. The public Vercel site uses a reviewed graph snapshot; it does not connect directly to the database.

The CloudFormation template creates a dedicated VPC, two private subnets, an S3 gateway endpoint, encrypted Neptune storage, IAM authentication, seven-day backups, deletion protection, and a private Lambda service for imports and bounded read queries. It creates no internet gateway, NAT gateway or public API. The bucket is retained if the stack is removed.

## Capacity

Neptune Serverless is configured for 1–2.5 NCU. It does not scale to zero. The November 13, 2026 Oregon Standard rate was $0.1608 per NCU-hour: approximately $117.38 per 730-hour month at minimum capacity, or $293.46 at the configured maximum for the entire month. Storage, I/O, backups beyond included allowances, S3 and Lambda charges are additional. The capacity setting is not an account spending limit.

Check the [current pricing](https://aws.amazon.com/neptune/pricing/) and [capacity documentation](https://docs.aws.amazon.com/neptune/latest/userguide/neptune-serverless-capacity-scaling.html) before creating another deployment.

## Rebuild and review

```sh
python3 infra/aws/build_template.py
aws cloudformation validate-template --template-body file://infra/aws/signalgraph-stack.json
```

Use an authenticated profile for the intended account and region. Review a CloudFormation change set before execution. The template uses an account-and-region-specific bucket name; it should not be used to create duplicate SignalGraph stacks in the same account and region.

## Import

Keep original inputs, primary records, review findings and canonical JSON outside the CSV loader prefix. Upload only the vertex and edge CSV files to `neptune/2026-11-13/` for this initial import. Hash and version each source archive. Change the fixed import prefix in `graph_service.py` for a new reviewed release, then regenerate and update the template.

The Lambda function supports `load`, `status`, `health`, `counts` and `connections`. Invoke through AWS IAM; there is no unauthenticated function URL. `connections` accepts an entity ID as a bound query parameter and returns at most 100 adjacent records. It does not accept arbitrary query text.

```json
{"action":"connections","entity_id":"IND_DONALD_TRUMP"}
```

After an import, inspect the complete loader result for errors, reconcile vertex and edge counts against the export validation, and inspect at least one ownership path and its source references. A successful upload or started loader is not proof of a successful database import.

## Publication

Maintain a reviewed snapshot for the public site. Corporate obligations, cash receipts, equity values, personal income and historical allegations have different meanings; the graph preserves their dates, recipients and qualifications. Correcting a claim should preserve the original archived record and record the revision. Never treat a missing amount as zero.

Public serving from Neptune would require a separately designed API and authentication boundary. The current implementation keeps database access private and publishes only the selected snapshot.
