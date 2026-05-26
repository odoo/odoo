./odoo-bin -d db1 -u base 

./odoo-bin -c ./odoo.conf

2026-05-21 10:17:01,957 220645 WARNING db4 odoo.modules.loading: The models ['estate_test_model', 'estate_property_model'] have no access rules in module estate, consider adding some, like:
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink


./odoo-bin -c ./odoo.conf --dev=all -i base