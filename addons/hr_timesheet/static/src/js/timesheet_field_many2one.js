/** @odoo-module alias=hr_timesheet.TimesheetFieldMany2one **/

import FieldRegistry from 'web.field_registry';
import { FieldMany2One } from 'web.relational_fields';

import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { Component } from "@odoo/owl";

const TimesheetFieldMany2one = FieldMany2One.extend({
    /**
     * @override
     * @private
     */
    _searchCreatePopup(view, ids, context, dynamicFilters) {
        const options = this._getSearchCreatePopupOptions(view, ids, context, dynamicFilters);
        Component.env.services.dialog.add(SelectCreateDialog, {
            title: options.title,
            resModel: options.res_model,
            multiSelect: false,
            domain: options.domain,
            context: options.context,
            noCreate: options.no_create,
            onSelected: (resId) => {
                return this.reinitialize(resId);
            },
            onClose: () => {
                this.activate();
            }
        });
    },
});

FieldRegistry.add('timesheet_field_many2one', TimesheetFieldMany2one);

export default TimesheetFieldMany2one;
