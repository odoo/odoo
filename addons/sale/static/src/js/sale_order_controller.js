odoo.define('sale.SaleOrderFormController', function (require) {
    "use strict";

    const FormController = require('web.FormController');
    const Dialog = require('web.Dialog');
    const core = require('web.core');
    const { sprintf } = require("web.utils");
    const _t = core._t;

    const SaleOrderFormController = FormController.extend({
        custom_events: _.extend({}, FormController.prototype.custom_events, {
            open_update_all_wizard: '_onOpenUpdateAllWizard',
        }),

        // -------------------------------------------------------------------------
        // Handlers
        // -------------------------------------------------------------------------

        /**
         * Handler called if user changes a value in the sale order line.
         * The wizard will open only if
         *  (1) Sale order line is 3 or more
         *  (2) First sale order line is changed
         *  (3) value is the same in all other sale order line
         */
        _onOpenUpdateAllWizard(ev) {
            const similarOrderLines = this._DialogReady(ev);
            const customValuesCommands = [];
            const confirmCallback = () => {
                similarOrderLines.slice(1).forEach((line) => {
                    customValuesCommands.push({
                        operation: "UPDATE",
                        id: line.id,
                        data: {[ev.data.fieldName]: ev.data.value},
                    });
                });
                this.trigger_up('field_changed', {
                            dataPointID: this.renderer.state.id,
                            changes: {order_line: {operation: "MULTI", commands: customValuesCommands}},
                });
            };
            if (similarOrderLines) {
                Dialog.confirm(this, this._getWizardMessage(ev), {
                    buttons: [{
                                text: _t('YES'),
                                classes: 'btn-primary',
                                close: true,
                                click: () => confirmCallback(),
                            }, {
                                text: _t("NO"),
                                close: true,
                    }],
                });
            }
        },

        _getWizardMessage (ev) {
            const fieldString = ev.target.string;
            const fieldType = ev.data.fieldType;
            let currentValue, newValue;
            if (fieldType === 'normal' || fieldType === 'date') {
                currentValue = ev.target.recordData[ev.data.fieldName];
                newValue = ev.data.value;
            } else if (fieldType === 'one2many') {
                currentValue = ev.target.recordData[ev.data.fieldName].data.display_name;
                newValue = ev.data.value.display_name;
            }
            return sprintf(_t(`Do you want to apply this new %s (%s) to other order lines with the same %s (%s)?`),
                            fieldString, newValue, fieldString, currentValue);
        },

        _getEqualValue (type, fieldName, fieldValue, orderLines) {
            let getEqualValue;
            if (type === 'normal') {
                getEqualValue = orderLines.filter(line => line.data[fieldName] === fieldValue);
            } else if (type == 'date') {
                getEqualValue = orderLines.filter(line => fieldValue.isSame(line.data[fieldName]));
            } else if (type === 'one2many') {
                // only works for display_name because we want to be able to apply different id with similar properties
                if (fieldValue.data && fieldValue.data.display_name) {
                    fieldValue = fieldValue.data.display_name;
                    getEqualValue = orderLines.filter(line => line.data[fieldName].data && line.data[fieldName].data.display_name === fieldValue);
                } else {
                    getEqualValue = orderLines.filter(line => line.data[fieldName].res_id === fieldValue.res_id);
                }
            } else if (type === 'many2many') {
                getEqualValue = orderLines.filter(line => (line.data[fieldName].res_ids.length == fieldValue.res_ids.length && line.data[fieldName].res_ids.every((val, index) => (val === fieldValue.res_ids[index]))));
            }
            return getEqualValue;
        },

        _DialogReady (ev) {
            const recordData = ev.target.recordData;
            const fieldName = ev.data.fieldName;
            const fieldValue = recordData[fieldName];
            const fieldType = ev.data.fieldType;
            const orderLines = this.renderer.state.data.order_line.data.filter(line => !line.data.display_type);
            const similarOrderLines = this._getEqualValue(fieldType, fieldName, fieldValue, orderLines);
            if (similarOrderLines && similarOrderLines.length < 3) {
                return false;
            }
            return similarOrderLines;
        },

    });

    return SaleOrderFormController;

});
