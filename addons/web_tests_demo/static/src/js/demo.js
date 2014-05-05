// static/src/js/demo.js
(function () {
    openerp.web_tests_demo = {
        value_true: true,
        SomeType: openerp.web.Class.extend({
            init: function (value) {
                this.value = value;
            }
        })
    };

}());
