/* eslint eqeqeq: [0, 0]*/
odoo.define('kw_remove_default_zero', function () {
    "use strict";

    var kw_remove_default_zero_func = function () {
        var value_string = $(this).val();
        value_string = value_string.replace(/[.:,]/g, '');
        if (value_string == 0 || value_string == '00:00') {
            $(this).val('');
        }
    };

    $(document)
        .on('click', '.o_field_float', kw_remove_default_zero_func)
        .on('click', '.o_input', kw_remove_default_zero_func);
});
