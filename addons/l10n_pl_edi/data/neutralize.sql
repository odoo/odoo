-- disable_l10n_pl_edi_integration

-- Delete customer's certificates
DELETE FROM certificate_certificate
      WHERE id IN (
                SELECT l10n_pl_edi_certificate
                  FROM l10n_pl_edi_config
               )
;

-- clear KSeF Credentials
UPDATE l10n_pl_edi_config
   SET l10n_pl_edi_certificate = NULL,
       l10n_pl_edi_session_id = NULL
;

-- Remove the attached binary data
DELETE FROM ir_attachment
      WHERE res_model = 'l10n_pl_edi.config'
        AND res_field IN ('l10n_pl_edi_session_key', 'l10n_pl_edi_session_iv')
;

-- set test environment parameter
     INSERT INTO ir_config_parameter (key, value, create_date, write_date)
          VALUES ('l10n_pl_edi_ksef.mode', 'test', NOW(), NOW())
     ON CONFLICT (key)
   DO UPDATE SET value = 'test',
                 write_date = NOW()
;
