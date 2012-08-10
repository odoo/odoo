openerp.auth_oauth = function(instance) {

    var QWeb = instance.web.qweb;

    instance.web.Login = instance.web.Login.extend({
        start: function() {
            console.log("Tu puta madre!");
            this._super.apply(this, arguments);
        },
        on_submit: function(ev) {
        },
        do_warn: function(title, msg) {
        },
        reset_error_message: function() {
        }
    });

};