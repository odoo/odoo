-- neutralize SUNAT delivery guide API connection
UPDATE res_company
SET l10n_pe_edi_stock_client_id = '',
    l10n_pe_edi_stock_client_secret = '',
    l10n_pe_edi_stock_client_username = '',
    l10n_pe_edi_stock_client_password = '',
    l10n_pe_edi_stock_token = '';