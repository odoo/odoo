odoo.define('web.datetime_tests', function (require) {
"use strict";

const datepicker = require("web.datepicker");
const testUtils = require("web.test_utils");

QUnit.module('DatePicker', {}, function () {

    QUnit.module('DateTimeWidget', {}, function () {

        QUnit.test("date time widget, selecting a date and clicking on input to close datepicker", async function (assert) {
            assert.expect(4);

            let counter = 0;
            testUtils.mock.patch(datepicker.DateTimeWidget, {
                _setValueFromUi: function () {
                    counter++;
                    return this._super.apply(this, arguments);
                },
            });

            const $target = $("#qunit-fixture");

            const parent = testUtils.createParent({});
            const dateTimeWidget = new datepicker.DateTimeWidget(parent);
            await dateTimeWidget.appendTo($target);

            // opening the datepicker
            await testUtils.dom.openDatepicker($target.find('.o_datepicker'));

            assert.strictEqual($('.bootstrap-datetimepicker-widget:visible').length, 1,
                "datepicker should be opened");
            assert.strictEqual(counter, 0, "counter should be 0");
            // selecting today's date (no date has been selected yet)
            testUtils.dom.click($('.day:contains(22)'));
            // now click on the input element, this should invoke _setValueFromUi() 2 times
            testUtils.dom.click(document.querySelector(".o_datepicker_input"));
            assert.strictEqual(counter, 2, "counter should be 0");

            // re-open datepicker
            testUtils.dom.openDatepicker($target.find('.o_datepicker'));
            assert.strictEqual($('.day.active').text(), '22',
                "datepicker should be highlight with 22nd day of month");

            dateTimeWidget.destroy();
            testUtils.mock.unpatch(datepicker.DateTimeWidget);
        });
    });
});
});
