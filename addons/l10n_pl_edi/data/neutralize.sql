-- disable_l10n_pl_edi_integration

-- clear KSeF Credentials
UPDATE res_company
   SET l10n_pl_edi_certificate = NULL,
       l10n_pl_edi_access_token = NULL,
       l10n_pl_edi_refresh_token = NULL,
       l10n_pl_edi_session_id = NULL,
       l10n_pl_edi_session_key = NULL,
       l10n_pl_edi_session_iv = NULL
;

-- set test environment parameter
     INSERT INTO ir_config_parameter (key, value, create_date, write_date)
          VALUES ('l10n_pl_edi_ksef.mode', 'test', NOW(), NOW())
     ON CONFLICT (key)
   DO UPDATE SET value = 'test',
                 write_date = NOW()
;
