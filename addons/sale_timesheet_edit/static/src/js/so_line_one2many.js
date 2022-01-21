odoo.define('sale_timesheet_edit.so_line_many2one', function (require) {
"use strict";

const fieldRegistry = require('web.field_registry');
const FieldOne2Many = require('web.relational_fields').FieldOne2Many;

const SoLineOne2Many = FieldOne2Many.extend({
    _onFieldChanged: function (ev) {
        if (
            ev.data.changes &&
            ev.data.changes.hasOwnProperty('timesheet_ids') &&
            ev.data.changes.timesheet_ids.operation === 'UPDATE' &&
            ev.data.changes.timesheet_ids.data &&
            ev.data.changes.timesheet_ids.data.hasOwnProperty('so_line')) {
            const line = this.value.data.find(line => {
                return line.id === ev.data.changes.timesheet_ids.id;
            });
            if (!line.is_so_line_edited) {
                ev.data.changes.timesheet_ids.data.is_so_line_edited = true;
            }
        }
        this._super.apply(this, arguments);
    }
});


fieldRegistry.add('so_line_one2many', SoLineOne2Many);

});
