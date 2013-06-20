openerp.crm_channel = function (instance) {
	instance.crm_channel = instance.crm_channel || {};
	instance.crm_channel.next_or_list = function(parent) {
		var form = parent.inner_widget.views.form.controller;
		form.dataset.remove_ids([form.dataset.ids[form.dataset.index]]);
		form.reload();
		if (!form.dataset.ids.length){
			parent.inner_widget.switch_mode('list');
		}
		parent.do_action({ type: 'ir.actions.act_window_close' });
	};
	instance.web.client_actions.add("next_or_list", "instance.crm_channel.next_or_list");
}