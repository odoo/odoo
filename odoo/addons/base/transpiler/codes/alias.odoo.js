odoo.define('@tests/alias', function (require) {
'use strict';
let __exports = {};

return __exports;
});

odoo.define(`tests.Alias`, function(require) {
    console.warn("tests.Alias is deprecated. Please use @tests/alias instead");
    return require('@tests/alias').__default;
});