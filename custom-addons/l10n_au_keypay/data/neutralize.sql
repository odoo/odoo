-- disable keypay integration
UPDATE res_company
   SET l10n_au_kp_enable = False,
       l10n_au_kp_identifier = '';

DELETE FROM ir_config_parameter
WHERE key IN ('l10n_au_keypay.l10n_au_kp_api_key', 'l10n_au_keypay.l10n_au_kp_base_url');
