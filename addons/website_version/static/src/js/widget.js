(function() {
    "use strict";

    var instance = openerp;
    openerp.website_version = instance.website_version || {};

    var module = instance.website_version;
    var QWeb   = instance.web.qweb;
    var _t = openerp._t;


    instance.website_version.rtoken = instance.web.form.AbstractField.extend({
        template: 'website_version.GoogleAccess',
        start: function() {
          var self = this;
          this.$el.on('click', 'button.GoogleAccess', function() {
              self.allow_google();
          });
      },
      allow_google: function() {
        var self = this;
        $('button.GoogleAccess').prop('disabled', true);
        var context = instance.web.pyeval.eval('context');
        self.rpc('/website_version/google_access', {
            fromurl: window.location.href,
            local_context: context
        }).done(function(o) {
            if (o.status === "need_auth") {
                alert(_t("You will be redirected to Google to authorize access to your Analytics Account!"));
                instance.web.redirect(o.url);
            }
            else if (o.status === "need_config_from_admin"){
              if (confirm(_t("The Google Management API key needs to be configured before you can use it, do you want to do it now?"))) {
                  self.do_action(o.action);
              }
            }
        }).always(function(o) { $('button.GoogleAccess').prop('disabled', false); });
      }

    });
    instance.web.form.widgets.add('rtoken', 'openerp.website_version.rtoken');
  

})();

