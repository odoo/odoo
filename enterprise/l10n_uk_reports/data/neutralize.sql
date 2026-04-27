-- disable HMRC
UPDATE ir_config_parameter
SET value = 'demo'
WHERE key = 'l10n_uk_reports.hmrc_mode';
