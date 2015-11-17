odoo.define('delivery.delivery', function (require) {

var ActionManager = require('web.ActionManager');
var framework = require('web.framework');

ActionManager.include({

    ir_actions_act_url: function (action) {
    	var self = this;
    
    	if ('url' in action && Array.isArray(action.url)){
	        if (action.target === 'self') {
	            framework.redirect(action.url);
	        } else {
	            this.dialog_stop();
	            _.each(action.url, function(url){ 
					window.open(url, '_blank');
				});
	        }
	        return $.when();
	     }
	    else {
	        return self._super(action);
    	}
    },	

});

});
