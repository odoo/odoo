// The goal of this test is to check the behavior of an onchange
// when changing values in the parent form having impacts
// on the one2many children while the child form is not visible
// The child model is defined with computed fields defined like:
// child.b = parent.a + 1
// child.c = child.b + 1
// child.d = child.c + 1
// a, b, c, d are all integer fields.
// a is a regular stored field
// b, c and d are computed fields, each one depending on the previous one.
// In the parent form view, when changing a, the children are visible
// with a tree view,
// with only the field b in the tree view (so without c and d).
// When opening a child, the child form view appears, with the field b, c and d.
// This test checks that, when opening a child, the dialog with the form appears
// with the expected values for the field b, c and d according to the value of a
// e.g., in the parent form, when changing a to 1,
// in the child form, b == 2, c == 3, d == 4
odoo.define('web.test.onchangespec', function (require) {
    'use strict';

    var tour = require("web_tour.tour");

    tour.register('on_change_spec', {
        url: '/web?debug=1#action=test_new_api.action_on_change_spec',
        test: true,
    }, [
    {
        content: "wait web client",
        trigger: '.breadcrumb:contains(On Change Spec)',
    }, {
        content: "create new record",
        trigger: 'button.o_list_button_add',
    }, {
        content: "set field name",
        trigger: 'input[name="name"]',
        run: 'text Test',
    }, {
        content: "set field a to 1",
        trigger: 'input[name="a"]',
        run: 'text 1',
    }, {
        content: 'add a child',
        trigger: 'div[name="child_ids"] a',
    }, {
        content: "check field b is equal to 2",
        trigger: '.o_field_integer[name="b"]:contains(2)',
        run: function () {}, // it's a check
    }, {
        content: "check field c is equal to 3",
        trigger: '.o_field_integer[name="c"]:contains(3)',
        run: function () {}, // it's a check
    }, {
        content: "check field d is equal to 4",
        trigger: '.o_field_integer[name="d"]:contains(4)',
        run: function () {}, // it's a check
    }, {
        content: "set name",
        trigger: 'input[name="name"]',
        run: 'text Test',
    }, {
        content: "save and close child",
        trigger: 'footer button:first-child',
    }, {
        content: "set field a to 2",
        trigger: 'input[name="a"]',
        run: 'text 2',
    }, {
        content: "re-open child",
        trigger: '.o_field_one2many[name="child_ids"] .o_data_row:first-child',
    }, {
        content: "check field b is equal to 3",
        trigger: '.o_field_integer[name="b"]:contains(3)',
        run: function () {}, // it's a check
    }, {
        content: "check field c is equal to 4",
        trigger: '.o_field_integer[name="c"]:contains(4)',
        run: function () {}, // it's a check
    }, {
        content: "check field d is equal to 5",
        trigger: '.o_field_integer[name="d"]:contains(5)',
        run: function () {}, // it's a check
    }]);
});
