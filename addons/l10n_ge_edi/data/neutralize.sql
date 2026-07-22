-- RS.ge serves its sandbox and its production system from the same endpoint, so the service-user
-- credentials are all that separates a copy of this database from the real taxpayer account.
UPDATE res_company
   SET l10n_ge_edi_su = NULL,
       l10n_ge_edi_sp = NULL;
