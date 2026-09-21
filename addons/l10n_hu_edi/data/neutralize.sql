-- Disable production mode for Hungary EDI
UPDATE l10n_hu_edi_config
   SET l10n_hu_edi_server_mode = 'test',
       l10n_hu_edi_username = ''
 WHERE l10n_hu_edi_server_mode = 'production';
