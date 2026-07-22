-- remove the credentials on sanitize
UPDATE res_company
   SET l10n_ge_edi_su = NULL,
       l10n_ge_edi_sp = NULL;
