odoo.define('web_tests_demo.demo', ['web.core'], function (require) {
"use strict";

var core = require('web.core');

var SomeType = core.Class.extend({
    init: function (value) {
        this.value = value;
    },
});

return {
    value_true: true,
    SomeType: SomeType,
};

});
