openerp.crm_partner_assign = function (instance) {
	instance.crm_partner_assign = instance.crm_partner_assign || {};
	instance.crm_partner_assign.next_or_list = function(parent) {
		if (parent.inner_widget.active_view === "form"){
			var form = parent.inner_widget.views.form.controller;
			form.dataset.remove_ids([form.dataset.ids[form.dataset.index]]);
			form.reload();
			if (!form.dataset.ids.length){
				parent.inner_widget.switch_mode('list');
			}
		}
		else{
			parent.inner_widget.views[parent.inner_widget.active_view].controller.reload();
		}
		parent.do_action({ type: 'ir.actions.act_window_close' });
	};
	instance.web.client_actions.add("next_or_list", "instance.crm_partner_assign.next_or_list");
}