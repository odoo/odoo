openerp.crm_partner_assign = function (instance) {
	instance.crm_partner_assign = instance.crm_partner_assign || {};
	instance.crm_partner_assign.next_or_list = function(parent) {
		var view = parent.inner_widget.active_view;
		var controller = parent.inner_widget.views[view].controller;
		if (view === "form"){
			if (controller.dataset.size()) {
	            controller.execute_pager_action('next');
	        } else {
	            controller.do_action('history_back');
	        }
    	}
		controller.do_action({ type: 'ir.actions.act_window_close' });
		if (view === "list"){
    		controller.records.remove(controller.records.get(parent.dialog_widget.action.context.active_id));
    	}
	};
	instance.web.client_actions.add("next_or_list", "instance.crm_partner_assign.next_or_list");
}