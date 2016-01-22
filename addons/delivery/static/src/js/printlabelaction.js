odoo.define('delivery.delivery', function (require) {

var ActionManager = require('web.ActionManager');
var framework = require('web.framework');

ActionManager.include({
    ir_actions_act_url: function (action, options) {
        if ('url' in action && _.isArray(action.url)){
            if (action.target === 'self') {
                framework.redirect(action.url);
            } else {
                if (!this.dialog) {
                    options.on_close();
                }
                this.dialog_stop();
                _.each(action.url, function(url){ 
                    window.open(url, '_blank');
                });
            }
            return $.when();
        } else {
            return this._super(action);
        }
    },
});

});
