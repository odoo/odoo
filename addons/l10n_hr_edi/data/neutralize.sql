-- reset MojEracun status
UPDATE res_company
SET l10n_hr_mer_username = NULL,
    l10n_hr_mer_password = NULL,
    l10n_hr_mer_company_ident = NULL,
    l10n_hr_mer_software_ident = NULL,
    l10n_hr_mer_connection_state = 'inactive',
    l10n_hr_mer_connection_mode = 'test';
