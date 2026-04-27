-- Set EDI to test mode (uses test and not production servers)
UPDATE res_company
   SET l10n_ec_production_env = false;
