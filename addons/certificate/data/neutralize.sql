UPDATE certificate_certificate
   SET pkcs12_password_plain = 'dummy',
       pkcs12_password_encrypted = NULL,
       certificate_credential_id = NULL;

UPDATE certificate_key
   SET password_plain = 'dummy',
       password_encrypted = NULL;
