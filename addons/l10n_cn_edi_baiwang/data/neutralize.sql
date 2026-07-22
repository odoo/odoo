UPDATE account_edi_proxy_client_user
   SET active = FALSE
 WHERE proxy_type = 'l10n_cn_edi_baiwang';

UPDATE res_company
   SET l10n_cn_edi_mode = 'test',
       l10n_cn_baiwang_subscription_status = 'not_subscribed',
       l10n_cn_baiwang_org_auth_code = NULL,
       l10n_cn_baiwang_last_request_id = NULL,
       l10n_cn_baiwang_cached_token = NULL,
       l10n_cn_baiwang_refresh_token = NULL,
       l10n_cn_baiwang_token_expiry = NULL;
