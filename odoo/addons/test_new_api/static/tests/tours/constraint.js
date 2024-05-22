odoo.define('web.test.constraint', function (require) {
    'use strict';

    var tour = require("web_tour.tour");
    var inc;

    tour.register('sql_constaint', {
        url: '/web?debug=1#action=test_new_api.action_categories',
        test: true,
    }, [
    {
        content: "wait web client",
        trigger: '.breadcrumb:contains(Categories)',
    }, { // create test category
        content: "create new category",
        trigger: 'button.o_list_button_add',
    }, {
        content: "insert content",
        trigger: 'input.o_required_modifier',
        run: 'text Test Category',
    }, { // try to insert a value that will raise the SQL constraint
        content: "insert invalid value",
        trigger: 'input[name="color"]',
        run: 'text -1',
    }, { // save
        content: "save category",
        trigger: 'button.o_form_button_save',
    }, { // check popup content
        content: "check notification box",
        trigger: '.o_dialog_warning:contains(The color code must be positive !)',
        run: function () {}, // it's a check
    }]);
});
