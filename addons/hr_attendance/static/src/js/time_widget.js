odoo.define('hr_attendance.widget', function (require) {
    "use strict";

    var basic_fields = require('web.basic_fields');
    var field_registry = require('web.field_registry');

    var RelativeTime = basic_fields.FieldDateTime.extend({
        _formatValue: function (val) {
            if (!(val && val._isAMomentObject)) {
                return;
            }
            return val.fromNow(true);
        },
    });

    field_registry.add('relative_time', RelativeTime);

    return RelativeTime;
});