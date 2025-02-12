-- disable l10n_pk_edi integration
UPDATE res_company
   SET l10n_pk_edi_pos_key = '123456',
       l10n_pk_edi_token = '906b1cd8-0d10-3a91-8234-8ec88e376bd6';
