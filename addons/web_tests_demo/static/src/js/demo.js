// static/src/js/demo.js
openerp.web_tests_demo = function (instance) {
    instance.web_tests_demo = {
        value_true: true,
        SomeType: instance.web.Class.extend({
            init: function (value) {
                this.value = value;
            }
        })
    };
};
