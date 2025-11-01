#!/usr/bin/env python3
"""
Encryption utilities for securing KiCAD design data.

This module provides client-side encryption using AWS KMS for protecting
sensitive schematic data before transmission to AI providers.
"""

import os
import json
import base64
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


@dataclass
class EncryptionConfig:
    """Configuration for encryption settings."""
    enabled: bool = False
    kms_key_id: Optional[str] = None
    aws_region: str = "us-east-1"
    
    @classmethod
    def from_env(cls) -> 'EncryptionConfig':
        """Load encryption configuration from environment variables."""
        return cls(
            enabled=os.getenv("ENABLE_ENCRYPTION", "false").lower() == "true",
            kms_key_id=os.getenv("AWS_KMS_KEY_ID"),
            aws_region=os.getenv("AWS_REGION", "us-east-1")
        )


class EncryptionManager:
    """
    Manages client-side encryption of sensitive design data using AWS KMS.
    
    This ensures that sensitive schematic information is encrypted before
    transmission to AI providers, with keys controlled by the customer.
    """
    
    def __init__(self, config: Optional[EncryptionConfig] = None):
        """
        Initialize encryption manager.
        
        Args:
            config: Encryption configuration. If None, loads from environment.
        """
        self.config = config or EncryptionConfig.from_env()
        self.kms_client = None
        
        if self.config.enabled:
            if not BOTO3_AVAILABLE:
                raise ImportError(
                    "boto3 is required for encryption. "
                    "Install with: pip install boto3"
                )
            
            if not self.config.kms_key_id:
                raise ValueError(
                    "AWS_KMS_KEY_ID environment variable must be set "
                    "when ENABLE_ENCRYPTION=true"
                )
            
            # Initialize AWS KMS client
            try:
                self.kms_client = boto3.client(
                    'kms',
                    region_name=self.config.aws_region
                )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize AWS KMS client: {e}")
    
    def encrypt_data(self, plaintext: str) -> Dict[str, str]:
        """
        Encrypt plaintext data using AWS KMS.
        
        Args:
            plaintext: The data to encrypt
            
        Returns:
            Dictionary containing encrypted data and metadata:
            {
                "ciphertext": base64-encoded encrypted data,
                "key_id": KMS key ID used for encryption,
                "encrypted": True
            }
        """
        if not self.config.enabled:
            return {
                "plaintext": plaintext,
                "encrypted": False
            }
        
        try:
            # Encrypt using KMS
            response = self.kms_client.encrypt(
                KeyId=self.config.kms_key_id,
                Plaintext=plaintext.encode('utf-8')
            )
            
            # Base64 encode the ciphertext for safe transmission
            ciphertext_b64 = base64.b64encode(
                response['CiphertextBlob']
            ).decode('utf-8')
            
            return {
                "ciphertext": ciphertext_b64,
                "key_id": response['KeyId'],
                "encrypted": True
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            raise RuntimeError(
                f"KMS encryption failed ({error_code}): {error_msg}"
            )
    
    def decrypt_data(self, encrypted_data: Dict[str, str]) -> str:
        """
        Decrypt data that was encrypted with AWS KMS.
        
        Args:
            encrypted_data: Dictionary containing encrypted data from encrypt_data()
            
        Returns:
            Decrypted plaintext string
        """
        if not encrypted_data.get("encrypted", False):
            return encrypted_data.get("plaintext", "")
        
        if not self.config.enabled:
            raise RuntimeError(
                "Cannot decrypt: encryption is not enabled"
            )
        
        try:
            # Base64 decode the ciphertext
            ciphertext = base64.b64decode(
                encrypted_data["ciphertext"]
            )
            
            # Decrypt using KMS
            response = self.kms_client.decrypt(
                CiphertextBlob=ciphertext
            )
            
            return response['Plaintext'].decode('utf-8')
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            raise RuntimeError(
                f"KMS decryption failed ({error_code}): {error_msg}"
            )
    
    def encrypt_schematic_data(self, schematic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive portions of schematic data.
        
        This selectively encrypts potentially sensitive fields while keeping
        metadata unencrypted for AI context.
        
        Args:
            schematic_data: Dictionary containing schematic information
            
        Returns:
            Dictionary with sensitive fields encrypted
        """
        if not self.config.enabled:
            return schematic_data
        
        encrypted = schematic_data.copy()
        
        # Fields to encrypt (containing potentially sensitive data)
        sensitive_fields = [
            'components',
            'nets', 
            'wires',
            'properties',
            'value',
            'lib_id'
        ]
        
        for field in sensitive_fields:
            if field in encrypted:
                # Convert to JSON string and encrypt
                field_json = json.dumps(encrypted[field])
                encrypted[field] = self.encrypt_data(field_json)
        
        return encrypted
    
    def decrypt_schematic_data(self, encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt schematic data that was encrypted with encrypt_schematic_data().
        
        Args:
            encrypted_data: Dictionary with encrypted fields
            
        Returns:
            Dictionary with all fields decrypted
        """
        if not self.config.enabled:
            return encrypted_data
        
        decrypted = encrypted_data.copy()
        
        # Decrypt any fields that are marked as encrypted
        for field, value in list(decrypted.items()):
            if isinstance(value, dict) and value.get("encrypted", False):
                decrypted_json = self.decrypt_data(value)
                decrypted[field] = json.loads(decrypted_json)
        
        return decrypted
    
    def sanitize_for_ai(self, text: str) -> str:
        """
        Sanitize text to remove PII before sending to AI.
        
        This is a basic implementation that should be extended based on
        specific requirements.
        
        Args:
            text: Text potentially containing PII
            
        Returns:
            Sanitized text with PII removed/redacted
        """
        # Basic email redaction
        import re
        sanitized = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL_REDACTED]',
            text
        )
        
        # Basic phone number redaction (US format)
        sanitized = re.sub(
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            '[PHONE_REDACTED]',
            sanitized
        )
        
        # Basic name patterns in comments (simple heuristic)
        # This is a basic implementation - extend as needed
        sanitized = re.sub(
            r'(designed by|author|engineer):\s*[A-Z][a-z]+\s+[A-Z][a-z]+',
            r'\1: [NAME_REDACTED]',
            sanitized,
            flags=re.IGNORECASE
        )
        
        return sanitized
