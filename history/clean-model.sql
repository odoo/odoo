
SELECT model, res_id, module FROM ir_model_data 
	WHERE model = 'ir.actions.act_window' 
	  AND NOT EXISTS (SELECT 1 FROM ir_act_window WHERE id = ir_model_data.res_id);


SELECT model, res_id, module FROM ir_model_data 
	WHERE model = 'ir.ui.menu' 
	  AND NOT EXISTS (SELECT 1 FROM ir_ui_menu WHERE id = ir_model_data.res_id);

SELECT model, res_id, module FROM ir_model_data 
	WHERE model = 'ir.ui.view' 
	  AND NOT EXISTS (SELECT 1 FROM ir_ui_view WHERE id = ir_model_data.res_id);

DONT DELETE FROM ir_model_data 
	WHERE model = 'ir.actions.act_window' 
	  AND NOT EXISTS (SELECT 1 FROM ir_act_window WHERE id = ir_model_data.res_id);
	  
DONT DELETE FROM ir_model_data 
	WHERE model = 'ir.ui.menu' 
	  AND NOT EXISTS (SELECT 1 FROM ir_ui_menu WHERE id = ir_model_data.res_id);
-- Other cleanups:
-- DELETE from ir_model_data where module = 'audittrail' AND model = 'ir.ui.view' AND NOT EXISTS( SELECT 1 FROM ir_ui_view WHERE ir_ui_view.id = ir_model_data.res_id);
-- DELETE from ir_model_data where module = 'audittrail' AND model = 'ir.ui.menu' AND NOT EXISTS( SELECT 1 FROM ir_ui_menu WHERE id = ir_model_data.res_id);