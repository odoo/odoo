-- disable l10n_ar afip integration
UPDATE res_company
   SET l10n_ar_afip_ws_environment = 'testing';

DELETE FROM ir_attachment
 WHERE res_model = 'res.company'
   AND res_field in ('l10n_ar_afip_ws_crt_id', 'l10n_ar_afip_ws_key_id');
