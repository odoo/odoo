odoo.define('sale_timesheet.so_line_many2one', function (require) {
"use strict";

const fieldRegistry = require('web.field_registry');
const { FieldOne2Many, FieldMany2One } = require('web.relational_fields');

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

const SoLineMany2one = FieldMany2One.extend({
    /**
     * @override
     *
     * When the user manually changes the field, we need to change the is_so_line_edited field in this model
     * to know the changes is manual and not via a compute method.
     */
    _onFieldChanged(ev) {
        if (ev.data.changes && ev.data.changes.hasOwnProperty('so_line') && !ev.data.changes.so_line.is_so_line_edited) {
            ev.data.changes.is_so_line_edited = true;
        }
        this._super.apply(this, arguments);
    },
});


fieldRegistry.add('so_line_one2many', SoLineOne2Many);
fieldRegistry.add('so_line_many2one', SoLineMany2one);

return SoLineOne2Many;

});
