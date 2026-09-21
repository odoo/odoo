-- disable l10n_eg_edi_eta integration
UPDATE l10n_eg_edi_eta_config
   SET l10n_eg_production_env = false;
