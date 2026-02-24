odoo.define('pragtech_ppc_ganttchart.widgets', function(require) {
	'use strict';

	var core = require('web.core');
	var Widget = require('web.Widget');
	var AbstractAction = require('web.AbstractAction');
	
	
	//Inside Variables
	var rent_product_list = new Array();
	var selected_days = new Array();
	
	var GanttView1 = AbstractAction.extend({
	    template: 'GanttView1',
	    events : {
	        "click .redirect_confirm" : "odoo_redirect",
	    },
	    init: function (parent, action) {
	        this._super(parent, action);
	        this.url = action.params.url;
	    },

	    odoo_redirect: function () {
	        window.open(this.url, '_blank');
	        this.do_action({type: 'ir.actions.act_window_close'});
	    },

	});
	core.action_registry.add('gantt_chart', GanttView1);


	
	$('#gantEditorTemplates').empty();
	$('#workSpace').empty();
	return {
		GanttView1 : GanttView1,
	};
	

});



