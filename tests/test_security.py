#!/usr/bin/env python3
"""
Tests for security features in KiCAD-Chat.
"""

import sys
import os
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test imports
from encryption import EncryptionConfig, EncryptionManager
from security_utils import validate_security_configuration, generate_security_report


def test_encryption_config():
    """Test encryption configuration loading."""
    print("Testing encryption configuration...")
    
    # Test default config
    config = EncryptionConfig()
    assert config.enabled == False, "Default should be disabled"
    assert config.aws_region == "us-east-1", "Default region should be us-east-1"
    print("✅ Default encryption config correct")
    
    # Test from environment
    os.environ["ENABLE_ENCRYPTION"] = "true"
    os.environ["AWS_KMS_KEY_ID"] = "test-key"
    os.environ["AWS_REGION"] = "us-west-2"
    
    config = EncryptionConfig.from_env()
    assert config.enabled == True, "Should be enabled from env"
    assert config.kms_key_id == "test-key", "Should load KMS key from env"
    assert config.aws_region == "us-west-2", "Should load region from env"
    print("✅ Encryption config loaded from environment")
    
    # Clean up
    del os.environ["ENABLE_ENCRYPTION"]
    del os.environ["AWS_KMS_KEY_ID"]
    del os.environ["AWS_REGION"]
    
    return True


def test_encryption_manager_disabled():
    """Test encryption manager when disabled."""
    print("\nTesting encryption manager (disabled mode)...")
    
    config = EncryptionConfig(enabled=False)
    manager = EncryptionManager(config)
    
    # Test that encryption is bypassed when disabled
    test_data = "sensitive schematic data"
    encrypted = manager.encrypt_data(test_data)
    
    assert encrypted["encrypted"] == False, "Should not be encrypted when disabled"
    assert encrypted["plaintext"] == test_data, "Should return plaintext when disabled"
    print("✅ Encryption manager correctly bypasses when disabled")
    
    return True


def test_sanitization():
    """Test PII sanitization."""
    print("\nTesting PII sanitization...")
    
    config = EncryptionConfig(enabled=False)
    manager = EncryptionManager(config)
    
    # Test email redaction
    text_with_email = "Contact: john.doe@example.com for questions"
    sanitized = manager.sanitize_for_ai(text_with_email)
    assert "[EMAIL_REDACTED]" in sanitized, "Should redact email"
    assert "john.doe@example.com" not in sanitized, "Should remove original email"
    print("✅ Email redaction works")
    
    # Test phone number redaction
    text_with_phone = "Call 555-123-4567 for support"
    sanitized = manager.sanitize_for_ai(text_with_phone)
    assert "[PHONE_REDACTED]" in sanitized, "Should redact phone"
    assert "555-123-4567" not in sanitized, "Should remove original phone"
    print("✅ Phone number redaction works")
    
    # Test name redaction in comments
    text_with_name = "Designed by: John Smith"
    sanitized = manager.sanitize_for_ai(text_with_name)
    assert "[NAME_REDACTED]" in sanitized, "Should redact name"
    print("✅ Name redaction works")
    
    return True


def test_security_validation():
    """Test security configuration validation."""
    print("\nTesting security configuration validation...")
    
    # Set minimal valid config
    os.environ["AI_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "test-key"
    os.environ["ENABLE_ENCRYPTION"] = "false"
    
    results = validate_security_configuration()
    
    assert "valid" in results, "Should have 'valid' field"
    assert isinstance(results["warnings"], list), "Should have warnings list"
    assert isinstance(results["recommendations"], list), "Should have recommendations list"
    assert isinstance(results["errors"], list), "Should have errors list"
    print("✅ Security validation structure correct")
    
    # Test warnings for disabled encryption
    assert len(results["warnings"]) > 0, "Should warn about disabled encryption"
    print("✅ Warnings generated for disabled encryption")
    
    # Clean up
    if "AI_PROVIDER" in os.environ:
        del os.environ["AI_PROVIDER"]
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    if "ENABLE_ENCRYPTION" in os.environ:
        del os.environ["ENABLE_ENCRYPTION"]
    
    return True


def test_security_report():
    """Test security report generation."""
    print("\nTesting security report generation...")
    
    # Set up environment
    os.environ["AI_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    test_path = Path("test_schematic.kicad_sch")
    report = generate_security_report(test_path)
    
    assert "SECURITY REPORT" in report, "Should have title"
    assert "test_schematic.kicad_sch" in report, "Should include filename"
    assert "Provider:" in report, "Should include provider"
    assert "Encryption:" in report, "Should include encryption status"
    print("✅ Security report generated successfully")
    print("\nSample report:")
    print(report)
    
    # Clean up
    if "AI_PROVIDER" in os.environ:
        del os.environ["AI_PROVIDER"]
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    return True


def test_schematic_data_encryption():
    """Test schematic data encryption/decryption."""
    print("\nTesting schematic data encryption (disabled mode)...")
    
    config = EncryptionConfig(enabled=False)
    manager = EncryptionManager(config)
    
    # Test data structure similar to actual schematic
    test_schematic = {
        "version": "20230121",
        "components": {
            "R1": {"value": "10k", "lib_id": "Device:R"},
            "R2": {"value": "4.7k", "lib_id": "Device:R"}
        },
        "nets": ["VCC", "GND"]
    }
    
    # Encrypt (should be no-op when disabled)
    encrypted = manager.encrypt_schematic_data(test_schematic)
    assert encrypted == test_schematic, "Should not modify data when disabled"
    print("✅ Schematic data passes through when encryption disabled")
    
    # Decrypt
    decrypted = manager.decrypt_schematic_data(encrypted)
    assert decrypted == test_schematic, "Should return original data"
    print("✅ Schematic data decryption works (disabled mode)")
    
    return True


def main():
    """Run all security tests."""
    print("🔒 KiCAD-Chat Security Tests\n")
    
    success = True
    
    try:
        success &= test_encryption_config()
        success &= test_encryption_manager_disabled()
        success &= test_sanitization()
        success &= test_security_validation()
        success &= test_security_report()
        success &= test_schematic_data_encryption()
    except AssertionError as e:
        print(f"\n❌ Assertion failed: {e}")
        success = False
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    if success:
        print("\n🎉 All security tests passed!")
        return 0
    else:
        print("\n❌ Some security tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
