-- disable bank synchronisation links
UPDATE account_online_link
   SET provider_data = '',
       client_id = 'duplicate';
