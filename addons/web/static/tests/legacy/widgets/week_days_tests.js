odoo.define('web.week_days_tests', function (require) {
    "use strict";

    const FormView = require('web.FormView');
    const testUtils = require('web.test_utils');

    QUnit.module('WeeklyRecurrence', {
        beforeEach() {
            this.data = {
                partner: {
                    fields: {
                        id: {strin: "id", type:"integer"},
                        mon: {string: "Mon", type: "boolean"},
                        tue: {string: "Tue", type: "boolean"},
                        wed: {string: "Wed", type: "boolean"},
                        thu: {string: "Thu", type: "boolean"},
                        fri: {string: "Fri", type: "boolean"},
                        sat: {string: "Sat", type: "boolean"},
                        sun: {string: "Sun", type: "boolean"},

                    },
                    records: [
                        {
                            id: 1,
                            mon: false,
                            tue: false,
                            wed: false,
                            thu: false,
                            fri: false,
                            sat: false,
                            sun: false,
                        },
                    ],
                },
            };
        },
    }, function () {
        QUnit.module('WeeklyRecurrenceWidget');

        QUnit.test('simple week recurrence widget', async function (assert) {
            assert.expect(14);

            let writeCall = 0;
            const form = await testUtils.createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                res_id: 1,
                arch:
                `<form string="Partners">
                    <sheet>
                        <group>
                            <widget name="week_days"/>
                        </group>
                    </sheet>
                </form>`,
                mockRPC: function (route, args) {
                    if (args.method === 'write') {
                        writeCall++;
                        if (writeCall === 1) {
                            assert.ok(args.args[1].sun,
                                "value of sunday should be true");
                            this.data.partner.records[0].sun = args.args[1].sun;
                        }
                        if (writeCall === 2) {
                            assert.notOk(args.args[1].sun,
                                "value of sunday should be false");
                            assert.ok(args.args[1].mon,
                                "value of monday should be true");
                            assert.ok(args.args[1].tue,
                                "value of tuesday should be true");
                            this.data.partner.records[0].sun = args.args[1].sun;
                            this.data.partner.records[0].mon = args.args[1].mon;
                            this.data.partner.records[0].tue = args.args[1].tue;
                        }
                        return Promise.resolve();
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.containsN(form, 'input:disabled', 7,
                "all inputs should be disabled in readonly mode");
            const labelsTexts = [...form.el.querySelectorAll('.o_recurrent_weekday_label')].map(el => el.innerText.trim());
            assert.deepEqual(labelsTexts, ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                "labels should be short week names");

            await testUtils.form.clickEdit(form);
            assert.containsNone(form, 'input:disabled', 7,
                "all inputs should be enabled in readonly mode");

            await testUtils.dom.click(form.el.querySelector('input[id^="sun"]'));
            assert.ok(form.el.querySelector('input[id^="sun"]').checked,
                "sunday checkbox should be checked");
            await testUtils.form.clickSave(form);

            await testUtils.form.clickEdit(form);
            await testUtils.dom.click(form.el.querySelector('input[id^="mon"]'));
            assert.ok(form.el.querySelector('input[id^="mon"]').checked,
                "monday checkbox should be checked");

            await testUtils.dom.click(form.el.querySelector('input[id^="tue"]'));
            assert.ok(form.el.querySelector('input[id^="tue"]').checked,
                "tuesday checkbox should be checked");

            // uncheck Sunday checkbox and check write call
            await testUtils.dom.click(form.el.querySelector('input[id^="sun"]'));
            assert.notOk(form.el.querySelector('input[id^="sun"]').checked,
                "sunday checkbox should be unchecked");

            await testUtils.form.clickSave(form);
            assert.notOk(form.el.querySelector('input[id^="sun"]').checked,
                "sunday checkbox should be unchecked");
            assert.ok(form.el.querySelector('input[id^="mon"]').checked,
                "monday checkbox should be checked");
            assert.ok(form.el.querySelector('input[id^="tue"]').checked,
                "tuesday checkbox should be checked");

            form.destroy();
        });

        QUnit.test('week recurrence widget show week start as per language configuration', async function (assert) {
            assert.expect(1);

            const form = await testUtils.createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                res_id: 1,
                arch:
                `<form string="Partners">
                    <sheet>
                        <group>
                            <widget name="week_days"/>
                        </group>
                    </sheet>
                </form>`,
                translateParameters: {
                    week_start: 5,
                },
            });

            const labelsTexts = [...form.el.querySelectorAll('.o_recurrent_weekday_label')].map(el => el.innerText.trim());
            assert.deepEqual(labelsTexts, ['Fri', 'Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu'],
                "labels should be short week names");

            form.destroy();
        });
    });
});
