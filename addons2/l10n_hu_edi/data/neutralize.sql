-- Disable production mode for Hungary EDI
UPDATE res_company
   SET l10n_hu_edi_server_mode = 'test',
       l10n_hu_edi_username = '',
       l10n_hu_edi_password = '',
       l10n_hu_edi_signature_key = '',
       l10n_hu_edi_replacement_key = ''
 WHERE l10n_hu_edi_server_mode = 'production';
