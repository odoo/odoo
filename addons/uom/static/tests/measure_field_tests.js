odoo.define('uom.MeasureFieldTests', function (require) {
    "use strict";

    const testUtils = require('web.test_utils');
    const FormView = require('web.FormView');
    const createView = testUtils.createView;
    const NotificationService = require('web.NotificationService');

    QUnit.module('fields', {}, function () {
        QUnit.module('MeasureField', {
            beforeEach: function () {
                this.data = {
                    line: {
                        fields: {
                            qty: {string: "qty", type: "measure"},
                            uom_id: {string: "uom", type: "many2one", relation: 'uom'},
                        },
                        records: [
                            {
                                id: 1,
                                qty: 8,
                                uom_id: 1,
                            },
                            {
                                id: 2,
                                qty: 1.2,
                                uom_id: 1,
                            },
                            {
                                id: 3,
                                qty: 1.333,
                                uom_id: 1,
                            },
                            {
                                id: 4,
                                qty: 999.99,
                                uom_id: 1,
                            },
                            {
                                id: 5,
                                qty: 999.99,
                                uom_id: 2,
                            },
                        ],
                    },
                    uom: {
                        fields: {
                            decimal_places: {string: 'decimal places', type: 'integer'},
                        },
                        records: [
                            {
                                id: 1,
                                decimal_places: 2,
                            },
                            {
                                id: 2,
                                decimal_places: 5,
                            },
                        ],
                    },
                };
            },
        }, function () {
            QUnit.test("Test display format of measure field", async function (assert) {
                assert.expect(5);

                var form = await createView({
                    View: FormView,
                    model: 'line',
                    data: this.data,
                    arch:'<form string="Lines">' +
                            '<field name="qty"/>' +
                            '<field name="uom_id"/>' +
                        '</form>',
                    res_id: 1,
                    session: {
                        uoms: {
                            1: {
                                decimal_places: 2,
                            },
                            2: {
                                decimal_places: 5,
                            },
                        }
                    },
                });
                assert.strictEqual($($('.o_field_widget')[0]).text(), "8.00");

                await form.reload({currentId: 2})
                assert.strictEqual($($('.o_field_widget')[0]).text(), "1.20");

                await form.reload({currentId: 3})
                assert.strictEqual($($('.o_field_widget')[0]).text(), "1.33");

                await form.reload({currentId: 4})
                assert.strictEqual($($('.o_field_widget')[0]).text(), "999.99");

                await form.reload({currentId: 5})
                assert.strictEqual($($('.o_field_widget')[0]).text(), "999.99000");

                form.destroy();
            });

            QUnit.test("Test edition of measure field, type more than the decimal places", async function (assert) {
                assert.expect(3);

                var form = await createView({
                    View: FormView,
                    model: 'line',
                    data: this.data,
                    arch:'<form string="Lines">' +
                            '<field name="qty"/>' +
                            '<field name="uom_id"/>' +
                        '</form>',
                    res_id: 1,
                    interceptsPropagate: {
                        call_service: function (ev) {
                            if (ev.data.service === 'notification') {
                                assert.strictEqual(ev.data.method, 'notify');
                                assert.strictEqual(ev.data.args[0].title, "Only 3 decimals are allowed.</br> This setting can be configured on the Unit of Measure.");
                            }
                        }
                    },
                    session: {
                        uoms: {
                            1: {
                                decimal_places: 3,
                                rounding: 0.001,
                            },
                        }
                    },
                });
                assert.strictEqual($($('.o_field_widget')[0]).text(), "8.000");

                await testUtils.form.clickEdit(form);

                let $input = form.$('input[name=qty]');
                await testUtils.fields.editInput($input, '8.0001');

                form.destroy();
            });

            QUnit.test("Test edition of measure field, type a value not matching the uom rounding", async function (assert) {
                assert.expect(3);

                var form = await createView({
                    View: FormView,
                    model: 'line',
                    data: this.data,
                    arch:'<form string="Lines">' +
                            '<field name="qty"/>' +
                            '<field name="uom_id"/>' +
                        '</form>',
                    res_id: 2,
                    interceptsPropagate: {
                        call_service: function (ev) {
                            if (ev.data.service === 'notification') {
                                assert.strictEqual(ev.data.method, 'notify');
                                assert.strictEqual(ev.data.args[0].title, "The rounding 0.05 is not respected.</br> This setting can be configured on the Unit of Measure.");
                            }
                        }
                    },
                    session: {
                        uoms: {
                            1: {
                                decimal_places: 2,
                                rounding: 0.05,
                            },
                        }
                    },
                });
                assert.strictEqual($($('.o_field_widget')[0]).text(), "1.20");

                await testUtils.form.clickEdit(form);

                let $input = form.$('input[name=qty]');
                await testUtils.fields.editInput($input, '1.23');

                form.destroy();
            });
        });
    });
});
