# Secure Data Transmission Framework - Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing the secure data transmission framework in KiCAD-Chat. This framework protects sensitive electronic design data when using AI services.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Basic Setup](#basic-setup)
3. [Anthropic Claude Integration](#anthropic-claude-integration)
4. [AWS KMS Encryption Setup](#aws-kms-encryption-setup)
5. [VPC/PrivateLink Configuration](#vpcprivatelink-configuration)
6. [Testing and Validation](#testing-and-validation)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required
- Python 3.10+
- OpenAI or Anthropic API key
- Basic understanding of environment variables

### Optional (for full security)
- AWS Account with KMS access
- Anthropic Enterprise contract with DPA
- AWS VPC with PrivateLink configured

## Basic Setup

### 1. Install Dependencies

```bash
# Clone repository
git clone https://github.com/WilliamxLeismer/KiCAD-Chat.git
cd KiCAD-Chat

# Install base dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your preferred editor
nano .env
```

### 3. Choose AI Provider

**Option A: OpenAI (Default)**
```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key-here
```

**Option B: Anthropic Claude (Recommended for sensitive data)**
```bash
# Install Anthropic SDK
pip install anthropic

# Configure in .env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### 4. Validate Configuration

```bash
python examples/security_example.py
```

## Anthropic Claude Integration

### Why Anthropic?

Anthropic Claude offers enhanced security features:
- **Zero Data Retention**: Data deleted within 24 hours
- **No Training**: Your data never enters model training
- **Enterprise DPA**: Legal guarantees for data protection
- **SOC 2 Compliance**: Audited security controls

### Setup Steps

#### 1. Get API Access

1. Sign up at [Anthropic Console](https://console.anthropic.com)
2. For production/sensitive data, contact Anthropic Enterprise sales
3. Request Zero Data Retention (ZDR) addendum

#### 2. Install SDK

```bash
pip install anthropic>=0.40.0
```

#### 3. Configure Environment

```bash
# .env file
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ZERO_RETENTION=true  # Requires Enterprise DPA
```

#### 4. Test Connection

```python
from anthropic_client import SecureAnthropicClient

client = SecureAnthropicClient()
response = client.create_message(
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.content)
```

## AWS KMS Encryption Setup

### Why Encryption?

Client-side encryption ensures:
- AI provider cannot access raw design files
- You control encryption keys (BYOK - Bring Your Own Key)
- Compliance with data protection regulations

### Setup Steps

#### 1. Create KMS Key

```bash
# Using AWS CLI
aws kms create-key \
    --description "KiCAD design file encryption" \
    --key-usage ENCRYPT_DECRYPT

# Create alias for easier reference
aws kms create-alias \
    --alias-name alias/kicad-design-key \
    --target-key-id <key-id-from-above>
```

#### 2. Configure IAM Permissions

Create IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/*"
    }
  ]
}
```

Attach to your IAM user or role:

```bash
aws iam put-user-policy \
    --user-name your-username \
    --policy-name KMSEncryptionPolicy \
    --policy-document file://kms-policy.json
```

#### 3. Install boto3

```bash
pip install boto3
```

#### 4. Configure Environment

```bash
# .env file
ENABLE_ENCRYPTION=true
AWS_KMS_KEY_ID=alias/kicad-design-key
AWS_REGION=us-east-1

# Configure AWS credentials (choose one):
# Option A: AWS CLI credentials
aws configure

# Option B: Environment variables
export AWS_ACCESS_KEY_ID=your-key-id
export AWS_SECRET_ACCESS_KEY=your-secret-key

# Option C: IAM role (recommended for EC2/ECS)
# No additional configuration needed
```

#### 5. Test Encryption

```bash
python tests/test_security.py
```

## VPC/PrivateLink Configuration

### Why PrivateLink?

- Traffic never leaves your private network
- Reduces attack surface
- Meets compliance requirements for data isolation

### Setup for Anthropic

#### 1. Contact Anthropic

Email Anthropic Enterprise support to enable PrivateLink for your account.

#### 2. Create VPC Endpoint

```bash
aws ec2 create-vpc-endpoint \
    --vpc-id vpc-12345678 \
    --service-name com.amazonaws.vpce.us-east-1.vpce-svc-anthropic \
    --vpc-endpoint-type Interface \
    --subnet-ids subnet-12345678 subnet-87654321 \
    --security-group-ids sg-12345678
```

#### 3. Configure Endpoint URL

```bash
# .env file
ANTHROPIC_ENDPOINT=https://vpce-12345-abcde.api.anthropic.com
```

#### 4. Test Connection

```python
from anthropic_client import SecureAnthropicClient

client = SecureAnthropicClient()
# Should connect through PrivateLink
response = client.create_message(
    messages=[{"role": "user", "content": "Test"}]
)
```

## Testing and Validation

### 1. Run Security Tests

```bash
# Test security features
python tests/test_security.py

# Test parser (regression check)
python tests/test_parser.py
```

### 2. Generate Security Report

```bash
python -c "
from pathlib import Path
from security_utils import generate_security_report

report = generate_security_report(Path('examples/simple.kicad_sch'))
print(report)
"
```

### 3. Validate Configuration

```bash
python -c "
from security_utils import validate_security_configuration

validation = validate_security_configuration()
print('Valid:', validation['valid'])
print('Errors:', validation['errors'])
print('Warnings:', validation['warnings'])
"
```

## Production Deployment

### Checklist

- [ ] **API Keys**: Never commit to version control
- [ ] **Encryption**: Enable for sensitive designs
- [ ] **Key Rotation**: Schedule quarterly KMS key rotation
- [ ] **Audit Logging**: Enable CloudTrail
- [ ] **Monitoring**: Set up alerts for API errors
- [ ] **Access Control**: Implement least privilege IAM
- [ ] **Backup**: Backup KMS keys to hardware security module
- [ ] **Documentation**: Document incident response procedures
- [ ] **Training**: Train team on security best practices
- [ ] **Review**: Quarterly security review of configuration

### Environment Variables (Production)

```bash
# AI Provider
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=${SECRET_MANAGER_ANTHROPIC_KEY}
ANTHROPIC_ENDPOINT=https://vpce-xxxxx.api.anthropic.com
ZERO_RETENTION=true

# Encryption
ENABLE_ENCRYPTION=true
AWS_KMS_KEY_ID=alias/kicad-production-key
AWS_REGION=us-east-1

# Audit & Compliance
AUDIT_LOGGING=true
USER_ID=${AUTHENTICATED_USER_ID}
SESSION_ID=${UNIQUE_SESSION_ID}
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt && \
    pip install anthropic boto3

COPY . .

# Don't include .env in image - use environment injection
ENV AI_PROVIDER=anthropic
ENV ENABLE_ENCRYPTION=true

CMD ["python", "kicad_chat.py"]
```

### Kubernetes Deployment

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: kicad-chat-secrets
type: Opaque
stringData:
  anthropic-api-key: sk-ant-xxxxx
  aws-access-key: AKIA...
  aws-secret-key: xxxxx

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kicad-chat
spec:
  template:
    spec:
      containers:
      - name: kicad-chat
        image: kicad-chat:latest
        env:
        - name: AI_PROVIDER
          value: "anthropic"
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: kicad-chat-secrets
              key: anthropic-api-key
        - name: ENABLE_ENCRYPTION
          value: "true"
        - name: AWS_KMS_KEY_ID
          value: "alias/kicad-production-key"
```

## Troubleshooting

### Common Issues

#### "boto3 is required for encryption"

**Solution**: Install boto3
```bash
pip install boto3
```

#### "ANTHROPIC_API_KEY not set"

**Solution**: Add to .env file
```bash
echo "ANTHROPIC_API_KEY=sk-ant-your-key" >> .env
```

#### "KMS encryption failed: AccessDeniedException"

**Solutions**:
1. Check IAM permissions include kms:Encrypt
2. Verify key ID is correct
3. Check AWS credentials are configured
4. Ensure key is in same region as configured

```bash
# Test KMS access
aws kms encrypt \
    --key-id alias/kicad-design-key \
    --plaintext "test" \
    --query CiphertextBlob \
    --output text
```

#### "Cannot connect to Anthropic API"

**Solutions**:
1. Check API key is valid
2. Verify endpoint URL (especially if using PrivateLink)
3. Check network connectivity
4. Review rate limits

```bash
# Test API connectivity
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'
```

#### "Zero retention not working"

**Solution**: 
- Zero retention requires Anthropic Enterprise DPA
- Contact Anthropic sales to enable
- Verify ZERO_RETENTION=true in .env

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Your code here
```

### Support

For issues:
1. Check [SECURITY.md](SECURITY.md) for detailed documentation
2. Review examples in `examples/security_example.py`
3. Run tests: `python tests/test_security.py`
4. Open GitHub issue with logs

## Next Steps

1. **Review**: Read [SECURITY.md](SECURITY.md) for threat model
2. **Test**: Run `examples/security_example.py`
3. **Deploy**: Follow production deployment checklist
4. **Monitor**: Set up CloudTrail and alerts
5. **Maintain**: Schedule quarterly security reviews

## Additional Resources

- [Anthropic Security Documentation](https://www.anthropic.com/security)
- [AWS KMS Best Practices](https://docs.aws.amazon.com/kms/latest/developerguide/best-practices.html)
- [AWS PrivateLink Documentation](https://docs.aws.amazon.com/vpc/latest/privatelink/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)

---

**Last Updated**: 2025-11-01  
**Version**: 1.0
