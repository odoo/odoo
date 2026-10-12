-- disable l10n_eg_edi_eta integration
UPDATE res_company
   SET l10n_eg_edi_api_mode = 'demo',
       l10n_eg_client_secret = 'dummy';
