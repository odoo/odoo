odoo.define('web.datetime_tests', function (require) {
"use strict";

var datepicker = require("web.datepicker");
var testUtils = require("web.test_utils");

QUnit.module('DatePicker', {}, function () {

    QUnit.module('DateTimeWidget', {}, function () {

        QUnit.test("in date time widget, changing a date and then clicking on input", async function (assert) {
            assert.expect(2);

            var $target = $("#qunit-fixture");

            var parent = testUtils.createParent({});
            var dateTimeWidget = new datepicker.DateTimeWidget(parent);

            testUtils.mock.patch(datepicker.DateTimeWidget, {
                _setValueFromUi: function () {
                    assert.ok(true, "should have triggered _setValueFromUi");
                    return this._super.apply(this, arguments);
                },
            });

            await dateTimeWidget.appendTo($target);
            // opening the datepicker
            await testUtils.dom.openDatepicker($target.find('.o_datepicker'));
            // selecting today's date (no date has been selected yet)
            testUtils.dom.click(document.querySelector(".datepicker-days > table > tbody > tr > td.day.today"));
            // now click on the input element, this should invoke _setValueFromUi() 2 times
            testUtils.dom.click(document.querySelector(".o_datepicker_input"));

            testUtils.mock.unpatch(datepicker.DateTimeWidget);
            dateTimeWidget.destroy();
        });
    });
});
});
