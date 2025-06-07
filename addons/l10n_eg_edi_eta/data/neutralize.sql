-- disable l10n_eg_edi_eta integration
UPDATE res_company
   SET l10n_eg_production_env = false,
       l10n_eg_client_secret = 'dummy';
