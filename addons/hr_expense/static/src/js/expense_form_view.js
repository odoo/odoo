odoo.define('hr_expense.FormView', function (require) {
"use strict";
    var Dialog = require('web.Dialog');

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');

    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var _t = core._t;

    var ExpenseFormController = FormController.extend({
        _onButtonClicked: function (ev) {
            if (ev.data.attrs.name === "action_submit_expenses") {
                ev.stopPropagation();
                var record = this.model.get(this.handle);
                if (record.data.duplicate_expense_ids.count) {
                    var _super = this._super.bind(this, ev);
                    const recordID = record.data.id;
                    this._showConfirmDialog(_super).then(() => {
                        return this._rpc({
                            model: 'hr.expense',
                            method: 'action_approve_duplicates',
                            args: [recordID],
                        });
                    });
                } else {
                    this._super.apply(this, arguments);
                }
            } else {
                this._super.apply(this, arguments);
            }
        },

        _showConfirmDialog: function(confirm_callback) {
            return new Promise(function (resolve, reject) {
                Dialog.confirm(this, _t("An expense of same category, amount and date already exists."), {
                    buttons: [
                        {
                            text: _t("Save Anyways"),
                            classes: 'btn-primary',
                            close: true,
                            click: function() {
                                confirm_callback();
                                resolve();
                            }
                        }, {
                            text: _t("Cancel"),
                            close: true,
                            click: reject,
                        }
                    ],
                });
            });
        }
    });

    var ExpenseFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: ExpenseFormController,
        }),
    });

    viewRegistry.add('hr_expense_form_view', ExpenseFormView);
});
