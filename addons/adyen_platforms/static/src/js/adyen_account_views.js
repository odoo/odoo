odoo.define('adyen_platforms.account_views', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var FormController = require('web.FormController');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');

var _t = core._t;
var QWeb = core.qweb;

var AdyenAccountFormController = FormController.extend({
    _saveRecord: function (recordID, options) {
        if(this.model.isNew(this.handle) && this.canBeSaved()) {
            var _super = this._super.bind(this, recordID, options);
            var buttons = [
                {
                    text: _t("Create"),
                    classes: 'btn-primary o_adyen_confirm',
                    close: true,
                    disabled: true,
                    click: function () {
                        this.close();
                        _super();
                    },
                },
                {
                    text: _t("Cancel"),
                    close: true,
                }
            ];

            var dialog = new Dialog(this, {
                size: 'extra-large',
                buttons: buttons,
                title: _t("Confirm your Adyen Account Creation"),
                $content: QWeb.render('AdyenAccountCreationConfirmation', {
                    data: this.model.get(this.handle).data,
                }),
            });

            dialog.open().opened(function () {
                dialog.$el.on('change', '.opt_in_checkbox', function (ev) {
                    ev.preventDefault();
                    dialog.$footer.find('.o_adyen_confirm')[0].disabled = !ev.currentTarget.checked;
                });
            });
        } else if (!this.model.isNew(this.handle)) {
            return this._super.apply(this, arguments);
        }
    },
});

var AdyenAccountFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: AdyenAccountFormController,
    }),
});

viewRegistry.add('adyen_account_form', AdyenAccountFormView);

});
