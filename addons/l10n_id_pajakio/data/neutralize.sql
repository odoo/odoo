-- disable l10n_id_pajakio integration and configs
UPDATE res_company
   SET l10n_id_pajakio_active = false,
       l10n_id_pajakio_mode = 'test',
       l10n_id_pajakio_key_identifier = NULL,
       l10n_id_pajakio_company_registered = false,
       l10n_id_pajakio_email = NULL;
