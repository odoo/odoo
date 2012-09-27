openerp.auth_oauth2_provider = function(instance) {

var QWeb = instance.web.qweb;
var _t = instance.web._t;

instance.web.client_actions.add('oauth2_auth', 'instance.auth_oauth2_provider.ProviderAction');
instance.auth_oauth2_provider.ProviderAction = instance.web.Widget.extend({
    template: "auth_oauth2_provider",
    start: function (parent) {
        var self = this;
        this._super.apply(this, arguments);
        this.params = $.deparam($.param.querystring());
        if (this.params.response_type !== 'token') {
            this.error(_t("Unsupported 'response_type' parameter"));
        }
        if (!this.params.redirect_uri) {
            this.error(_t("No 'redirect_uri' parameter given"));
        }

        if (!this._error) {
            var confirmation = this.params.approval_prompt || 'none';
            var was_already_logged = true; // TODO: how can I know this ?
            if (confirmation === 'force' || (confirmation === 'auto' && !was_already_logged)) {
                this.$('.oe_oauth2_provider_approval').show()
                    .on('click', '.oe_oauth2_provider_allow', this.on_confirm)
                    .on('click', '.oe_oauth2_provider_deny', this.on_reject);
            } else {
                this.on_confirm();
            }
        }
    },
    on_confirm: function() {
        var self = this;
        instance.session.rpc('/oauth2/get_token', {
            client_id: this.params.client_id || '',
            scope: this.params.scope || '',
        }).then(function(result) {
            self.redirect(result);
        }).fail(function() {
            self.error(_t("An error occured while contacting the OpenERP server."));
        });
    },
    on_reject: function() {
        this.redirect({
            error: 'access_denied'
        });
    },
    redirect: function(result) {
        var params = $.deparam($.param.querystring());
        var a = document.createElement('a');
        a.href = params.redirect_uri;
        var new_params = {};
        if (!result.error) {
            new_params.access_token = result.access_token;
            new_params.token_type = 'Bearer';
            if (result.expires_in) {
                new_params.expires_in = result.expires_in;
            }
        } else {
            new_params.error = result.error;
        }
        if (params.state) {
            new_params.state = params.state;
        }
        var redirect = params.redirect_uri + (a.hash ? '&' : '#') + $.param(new_params);

        // Hack in order to avoid pending request failure notification
        // TODO: a stop() method on webclient wich will return a deferred resolved when pending
        //       rpc calls are done
        instance.session.on_rpc_error = function() { };
        window.location = redirect;
    },
    error: function(msg) {
        this._error = true;
        var $msg = $('<li/>').addClass('oe_oauth2_provider_error_text').text(msg);
        $msg.appendTo(this.$('.oe_oauth2_provider_error').show().find('ul'));
        return false;
    },
});

};
