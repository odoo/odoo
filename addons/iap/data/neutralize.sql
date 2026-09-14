-- encrypted tokens cannot be suffixed with +disabled here; iap.account.get() replaces unlinked accounts with disabled ones
UPDATE iap_account
   SET credential_id = NULL
 WHERE credential_id IS NOT NULL;
