odoo.define('website_form.website_form_editor', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var options = require('web_editor.snippets.options');

var QWeb = core.qweb;
var _t = core._t;

options.registry.default_contact_form_editor = options.Class.extend({
    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Open dialog to change recipient email address.
     */
    changeRecipientEmail: function () {
        var self = this;
        var email = this.$target.find('[name="email_to"]').val();
        if (!email) {
            var $valueNode = this.$target.nearest('[data-for]');
            var values = JSON.parse($valueNode.data('values').replace(/'/g, '"'));
            email = values['email_to'];
        }
        new Dialog(this, {
            size: 'medium',
            title: _t("Change Recipient Email"),
            $content: QWeb.render('website_form.default_contact_form_editor', {email: email}),
            buttons: [
                {
                    text: _t("Save"),
                    classes: 'btn-primary',
                    close: true,
                    click: function () {
                        self.$target.find('[name="email_to"]').attr('value', this.$('input').val().trim());
                    },
                }, {
                    text: _t("Cancel"),
                    close: true,
                },
            ],
        }).open();
    }
});

});
