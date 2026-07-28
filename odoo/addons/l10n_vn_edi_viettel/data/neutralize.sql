-- disable l10n_vn_edi integration
UPDATE res_company
   SET l10n_vn_edi_username = '',
       l10n_vn_edi_password = '';
