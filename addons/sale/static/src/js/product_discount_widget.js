odoo.define('sale.update_line_widget', function (require) {
    "use strict";

    const BasicFields = require('web.basic_fields');
    const FieldsRegistry = require('web.field_registry');
    const UpdateAllLinesMixin = require('sale.UpdateAllLinesMixin');

    const FloatUpdateAllLines = BasicFields.FieldFloat.extend(UpdateAllLinesMixin, {
        _getUpdateAllLinesAction: function () {
            return 'open_update_all_wizard';
        },
    });

    FieldsRegistry.add('float_update_lines', FloatUpdateAllLines);

    return {
        FloatUpdateAllLines: FloatUpdateAllLines,
    };

});
