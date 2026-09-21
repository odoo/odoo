-- reset MojEracun status
UPDATE l10n_hr_edi_config
SET l10n_hr_mer_username = NULL,
    l10n_hr_mer_company_ident = NULL,
    l10n_hr_mer_software_ident = NULL,
    l10n_hr_mer_connection_state = 'inactive',
    l10n_hr_mer_connection_mode = 'test';
