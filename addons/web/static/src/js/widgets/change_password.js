odoo.define('web.ChangePassword', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var web_client = require('web.web_client');

var _t = core._t;

var ChangePassword = Widget.extend({ // FIXME
    template: "ChangePassword",
    start: function() {
        var self = this;
        web_client.set_title(_t("Change Password"));
        var $button = self.$('.oe_form_button');
        $button.appendTo(this.getParent().$footer);
        $button.eq(1).click(function(){
           self.$el.parents('.modal').modal('hide');
        });
        $button.eq(0).click(function(){
          self.rpc("/web/session/change_password",{
               'fields': $("form[name=change_password_form]").serializeArray()
          }).done(function(result) {
               if (result.error) {
                  self.display_error(result);
                  return;
               } else {
                  self.do_action('logout');
               }
          });
       });
    },
    display_error: function (error) {
        return new Dialog(this, {
            size: 'medium',
            title: error.title,
            $content: $('<div>').html(error.error)
        }).open();
    },
});

core.action_registry.add("change_password", ChangePassword);

return ChangePassword;
});
