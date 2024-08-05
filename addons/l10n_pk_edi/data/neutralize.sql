-- disable l10n_pk_edi integration
UPDATE res_company
   SET l10n_pk_edi_pos_key = NULL,
       l10n_pk_edi_token = NULL;
