openerp.auth_oauth_provider = function(instance) {

var QWeb = instance.web.qweb;
var _t = instance.web._t;

instance.web.client_actions.add('oauth2_auth', 'instance.auth_oauth_provider.ProviderAction');
instance.auth_oauth_provider.ProviderAction = instance.web.Widget.extend({
    template: "auth_oauth_provider",
    start: function (parent) {
        var self = this;
        this._super.apply(this, arguments);
        var params = $.deparam($.param.querystring());
        if (params.response_type !== 'token') {
            this.error(_t("Unsupported 'response_type' parameter"));
        }
        if (!params.redirect_uri) {
            this.error(_t("No 'redirect_uri' parameter given"));
        }
        // params.client_id
        // TODO: check if client_id application is authorized to use the service, and get it's name
        // that should be displayed in the approval confirmation dialog.

        if (!this._error) {
            // params.approval_prompt TODO --> add 'none' (default)
            // TODO: get client_id and scope
            this.$('.oe_oauth_provider_approval').show().on('click', '.oe_oauth_provider_allow', function() {
                instance.session.rpc('/oauth2/get_token', {
                    client_id: params.client_id || '',
                    scope: params.scope || '',
                }).then(function(result) {
                    self.redirect(result);
                }).fail(function() {
                    self.error(_t("An error occured while contacting the OpenERP server."));
                });
            }).on('click', '.oe_oauth_provider_deny', function() {
                self.redirect({
                    error: 'access_denied'
                });
            });
        }
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
        var redirect = a.protocol + '//' + a.host + a.pathname + '?' + $.param(new_params) + a.hash;
        //window.location = redirect;
        console.log("redirect to", redirect);
    },
    error: function(msg) {
        this._error = true;
        var $msg = $('<li/>').addClass('oe_oauth_provider_error_text').text(msg);
        $msg.appendTo(this.$('.oe_oauth_provider_error').show().find('ul'));
        return false;
    },
});

};
