-- disable AvaTax
UPDATE res_company
   SET avalara_environment = 'sandbox';
UPDATE account_fiscal_position
   SET is_avatax = false;
