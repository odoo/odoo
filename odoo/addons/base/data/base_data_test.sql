---------------------------------
-- Test data adaptation
---------------------------------
select setval('res_currency_id_seq', 97);
update res_currency set id = 97;
update ir_model_data set res_id = 97 where model = 'res.currency';

select setval('res_company_id_seq', 21);
update res_company set id = 21, partner_id = 11, currency_id = 97;
update ir_model_data set res_id = 21 where model = 'res.company';

select setval('res_partner_id_seq', 11);
update res_partner set id = 11, company_id = 21;
update ir_model_data set res_id = 11 where model = 'res.partner';

-- no change for seq for user
update res_users set partner_id = 11, company_id = 21;

select setval('res_groups_id_seq', 71);
update res_groups set id = 71;
update ir_model_data set res_id = 71 where model = 'res.groups';
