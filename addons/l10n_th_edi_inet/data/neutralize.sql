-- disable l10n_th_edi_inet production environment
UPDATE res_company
   SET l10n_th_edi_inet_staging_mode = TRUE;
