
SELECT model, res_id, module FROM ir_model_data 
	WHERE model = 'ir.actions.act_window' 
	  AND NOT EXISTS (SELECT 1 FROM ir_act_window WHERE id = ir_model_data.res_id);