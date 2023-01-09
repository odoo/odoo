odoo.define('web.datepicker_tests', function (require) {
    "use strict";

    const { DatePicker, DateTimePicker } = require('web.DatePickerOwl');
    const testUtils = require('web.test_utils');
    const time = require('web.time');

    const { createComponent } = testUtils;

    QUnit.module('Components', {}, function () {

        QUnit.module('DatePicker (legacy)');

        QUnit.test("basic rendering", async function (assert) {
            assert.expect(8);

            const picker = await createComponent(DatePicker, {
                props: { date: moment('1997-01-09'), onDateTimeChanged: () => {} },
            });


            assert.containsOnce(picker, 'input.o_input.o_datepicker_input');
            assert.containsOnce(picker, 'span.o_datepicker_button');
            assert.containsNone(document.body, 'div.bootstrap-datetimepicker-widget');

            const input = picker.el.querySelector('input.o_input.o_datepicker_input');
            assert.strictEqual(input.value, '01/09/1997',
                "Value should be the one given")
                ;
            assert.strictEqual(input.dataset.target, `#${picker.el.id}`,
                "DatePicker id should match its input target");

            await testUtils.dom.click(input);

            assert.containsOnce(document.body, 'div.bootstrap-datetimepicker-widget .datepicker');
            assert.containsNone(document.body, 'div.bootstrap-datetimepicker-widget .timepicker');
            assert.strictEqual(
                document.querySelector('.datepicker .day.active').dataset.day,
                '01/09/1997',
                "Datepicker should have set the correct day"
            );
        });

        QUnit.test("pick a date", async function (assert) {
            assert.expect(5);

            const picker = await createComponent(DatePicker, {
                props: {
                    date: moment('1997-01-09'),
                    onDateTimeChanged: date => {
                        assert.step('datetime-changed');
                        assert.strictEqual(date.format('MM/DD/YYYY'), '02/08/1997',
                            "Event should transmit the correct date");
                    },
                }
            });
            const input = picker.el.querySelector('.o_datepicker_input');

            await testUtils.dom.click(input);
            await testUtils.dom.click(document.querySelector('.datepicker th.next')); // next month

            assert.verifySteps([]);

            await testUtils.dom.click(document.querySelectorAll('.datepicker table td')[15]); // previous day

            assert.strictEqual(input.value, '02/08/1997');
            assert.verifySteps(['datetime-changed']);
        });

        QUnit.test("pick a date with locale", async function (assert) {
            assert.expect(4);

            // weird shit of moment https://github.com/moment/moment/issues/5600
            // When month regex returns undefined, january is taken (first month of the default "nameless" locale)
            const originalLocale = moment.locale();
            // Those parameters will make Moment's internal compute stuff that are relevant to the bug
            const months = 'janvier_février_mars_avril_mai_juin_juillet_août_septembre_octobre_novembre_décembre'.split('_');
            const monthsShort = 'janv._févr._mars_avr._mai_juin_juil._août_custSept._oct._nov._déc.'.split('_');
            moment.defineLocale('frenchForTests', { months, monthsShort, code: 'frTest' , monthsParseExact: true});

            const hasChanged = testUtils.makeTestPromise();
            const picker = await createComponent(DatePicker, {
                translateParameters: {
                    date_format: "%d %b, %Y", // Those are important too
                    time_format: "%H:%M:%S",
                },
                props: {
                    date: moment('09/01/1997', 'MM/DD/YYYY'),
                    onDateTimeChanged: date => {
                        assert.step('datetime-changed');
                        assert.strictEqual(date.format('MM/DD/YYYY'), '09/02/1997',
                            "Event should transmit the correct date");
                        hasChanged.resolve();
                    },
                }
            });
            const input = picker.el.querySelector('.o_datepicker_input');
            await testUtils.dom.click(input);

            await testUtils.dom.click(document.querySelectorAll('.datepicker table td')[3]); // next day

            assert.strictEqual(input.value, '02 custSept., 1997');
            assert.verifySteps(['datetime-changed']);

            moment.locale(originalLocale);
            moment.updateLocale('frenchForTests', null);
        });

        QUnit.test("enter a date value", async function (assert) {
            assert.expect(5);

            const picker = await createComponent(DatePicker, {
                props: {
                    date: moment('1997-01-09'),
                    onDateTimeChanged: date => {
                        assert.step('datetime-changed');
                        assert.strictEqual(date.format('MM/DD/YYYY'), '02/08/1997',
                            "Event should transmit the correct date");
                    },
                }
            });
            const input = picker.el.querySelector('.o_datepicker_input');

            assert.verifySteps([]);

            await testUtils.fields.editAndTrigger(input, '02/08/1997', ['change']);

            assert.verifySteps(['datetime-changed']);

            await testUtils.dom.click(input);

            assert.strictEqual(
                document.querySelector('.datepicker .day.active').dataset.day,
                '02/08/1997',
                "Datepicker should have set the correct day"
            );
        });

        QUnit.test("Date format is correctly set", async function (assert) {
            assert.expect(2);

            testUtils.mock.patch(time, { getLangDateFormat: () => "YYYY/MM/DD" });
            const picker = await createComponent(DatePicker, {
                props: { date: moment('1997-01-09'), onDateTimeChanged: () => {} },
            });
            const input = picker.el.querySelector('.o_datepicker_input');

            assert.strictEqual(input.value, '1997/01/09');

            // Forces an update to assert that the registered format is the correct one
            await testUtils.dom.click(input);

            assert.strictEqual(input.value, '1997/01/09');

            testUtils.mock.unpatch(time);
        });

        QUnit.module('DateTimePicker (legacy)');

        QUnit.test("basic rendering", async function (assert) {
            assert.expect(11);

            const picker = await createComponent(DateTimePicker, {
                props: { date: moment('1997-01-09 12:30:01'), onDateTimeChanged: () => {} },
            });

            assert.containsOnce(picker, 'input.o_input.o_datepicker_input');
            assert.containsOnce(picker, 'span.o_datepicker_button');
            assert.containsNone(document.body, 'div.bootstrap-datetimepicker-widget');

            const input = picker.el.querySelector('input.o_input.o_datepicker_input');
            assert.strictEqual(input.value, '01/09/1997 12:30:01', "Value should be the one given");
            assert.strictEqual(input.dataset.target, `#${picker.el.id}`,
                "DateTimePicker id should match its input target");

            await testUtils.dom.click(input);

            assert.containsOnce(document.body, 'div.bootstrap-datetimepicker-widget .datepicker');
            assert.containsOnce(document.body, 'div.bootstrap-datetimepicker-widget .timepicker');
            assert.strictEqual(
                document.querySelector('.datepicker .day.active').dataset.day,
                '01/09/1997',
                "Datepicker should have set the correct day");

            assert.strictEqual(document.querySelector('.timepicker .timepicker-hour').innerText.trim(), '12',
                "Datepicker should have set the correct hour");
            assert.strictEqual(document.querySelector('.timepicker .timepicker-minute').innerText.trim(), '30',
                "Datepicker should have set the correct minute");
            assert.strictEqual(document.querySelector('.timepicker .timepicker-second').innerText.trim(), '01',
                "Datepicker should have set the correct second");
        });

        QUnit.test("pick a date and time", async function (assert) {
            assert.expect(5);

            const picker = await createComponent(DateTimePicker, {
                props: {
                    date: moment('1997-01-09 12:30:01'),
                    onDateTimeChanged: date => {
                        assert.step('datetime-changed');
                        assert.strictEqual(date.format('MM/DD/YYYY HH:mm:ss'), '02/08/1997 15:45:05',
                            "Event should transmit the correct date");
                    },
                }
            });
            const input = picker.el.querySelector('input.o_input.o_datepicker_input');

            await testUtils.dom.click(input);
            await testUtils.dom.click(document.querySelector('.datepicker th.next')); // February
            await testUtils.dom.click(document.querySelectorAll('.datepicker table td')[15]); // 08
            await testUtils.dom.click(document.querySelector('a[title="Select Time"]'));
            await testUtils.dom.click(document.querySelector('.timepicker .timepicker-hour'));
            await testUtils.dom.click(document.querySelectorAll('.timepicker .hour')[15]); // 15h
            await testUtils.dom.click(document.querySelector('.timepicker .timepicker-minute'));
            await testUtils.dom.click(document.querySelectorAll('.timepicker .minute')[9]); // 45m
            await testUtils.dom.click(document.querySelector('.timepicker .timepicker-second'));

            assert.verifySteps([]);

            await testUtils.dom.click(document.querySelectorAll('.timepicker .second')[1]); // 05s

            assert.strictEqual(input.value, '02/08/1997 15:45:05');
            assert.verifySteps(['datetime-changed']);
        });

        QUnit.test("pick a date and time with locale", async function (assert) {
            assert.expect(5);

            // weird shit of moment https://github.com/moment/moment/issues/5600
            // When month regex returns undefined, january is taken (first month of the default "nameless" locale)
            const originalLocale = moment.locale();
            // Those parameters will make Moment's internal compute stuff that are relevant to the bug
            const months = 'janvier_février_mars_avril_mai_juin_juillet_août_septembre_octobre_novembre_décembre'.split('_');
            const monthsShort = 'janv._févr._mars_avr._mai_juin_juil._août_custSept._oct._nov._déc.'.split('_');
            moment.defineLocale('frenchForTests', { months, monthsShort, code: 'frTest' , monthsParseExact: true});

            const hasChanged = testUtils.makeTestPromise();
            const picker = await createComponent(DateTimePicker, {
                translateParameters: {
                    date_format: "%d %b, %Y", // Those are important too
                    time_format: "%H:%M:%S",
                },
                props: {
                    date: moment('09/01/1997 12:30:01', 'MM/DD/YYYY HH:mm:ss'),
                    onDateTimeChanged: date => {
                        assert.step('datetime-changed');
                        assert.strictEqual(date.format('MM/DD/YYYY HH:mm:ss'), '09/02/1997 15:45:05',
                            "Event should transmit the correct date");
                        hasChanged.resolve();
                    },
                }
            });

            const input = picker.el.querySelector('input.o_input.o_datepicker_input');

            await testUtils.dom.click(input);
            await testUtils.dom.click(document.querySelectorAll('.datepicker table td')[3]); // next day
            await testUtils.dom.click(document.querySelector('a[title="Select Time"]'));
            await testUtils.dom.click(document.querySelector('.timepicker .timepicker-hour'));
            await testUtils.dom.click(document.querySelectorAll('.timepicker .hour')[15]); // 15h
            await testUtils.dom.click(document.querySelector('.timepicker .timepicker-minute'));
            await testUtils.dom.click(document.querySelectorAll('.timepicker .minute')[9]); // 45m
            await testUtils.dom.click(document.querySelector('.timepicker .timepicker-second'));

            assert.verifySteps([]);
            await testUtils.dom.click(document.querySelectorAll('.timepicker .second')[1]); // 05s

            assert.strictEqual(input.value, '02 custSept., 1997 15:45:05');
            assert.verifySteps(['datetime-changed']);

            await hasChanged;

            moment.locale(originalLocale);
            moment.updateLocale('frenchForTests', null);
        });

        QUnit.test("enter a datetime value", async function (assert) {
            assert.expect(9);

            const picker = await createComponent(DateTimePicker, {
                props: {
                    date: moment('1997-01-09 12:30:01'),
                    onDateTimeChanged: date => {
                        assert.step('datetime-changed');
                        assert.strictEqual(date.format('MM/DD/YYYY HH:mm:ss'), '02/08/1997 15:45:05',
                            "Event should transmit the correct date");
                    },
                }
            });
            const input = picker.el.querySelector('.o_datepicker_input');

            assert.verifySteps([]);

            await testUtils.fields.editAndTrigger(input, '02/08/1997 15:45:05', ['change']);

            assert.verifySteps(['datetime-changed']);

            await testUtils.dom.click(input);

            assert.strictEqual(input.value, '02/08/1997 15:45:05');
            assert.strictEqual(
                document.querySelector('.datepicker .day.active').dataset.day,
                '02/08/1997',
                "Datepicker should have set the correct day"
            );
            assert.strictEqual(document.querySelector('.timepicker .timepicker-hour').innerText.trim(), '15',
                "Datepicker should have set the correct hour");
            assert.strictEqual(document.querySelector('.timepicker .timepicker-minute').innerText.trim(), '45',
                "Datepicker should have set the correct minute");
            assert.strictEqual(document.querySelector('.timepicker .timepicker-second').innerText.trim(), '05',
                "Datepicker should have set the correct second");
        });

        QUnit.test("Date time format is correctly set", async function (assert) {
            assert.expect(2);

            testUtils.mock.patch(time, { getLangDatetimeFormat: () => "hh:mm:ss YYYY/MM/DD" });
            const picker = await createComponent(DateTimePicker, {
                props: { date: moment('1997-01-09 12:30:01'), onDateTimeChanged: () => {} },
            });
            const input = picker.el.querySelector('.o_datepicker_input');

            assert.strictEqual(input.value, '12:30:01 1997/01/09');

            // Forces an update to assert that the registered format is the correct one
            await testUtils.dom.click(input);

            assert.strictEqual(input.value, '12:30:01 1997/01/09');

            testUtils.mock.unpatch(time);
        });
    });
});
