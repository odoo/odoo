odoo.define('event.configurator.tests', function (require) {
    "use strict";

    var FormView = require('web.FormView');
    var testUtils = require('web.test_utils');
    var createView = testUtils.createView;

    var getArch = function (){
        return '<form>' +
        '<sheet>' +
        '<field name="sale_order_line" widget="section_and_note_one2many">' +
        '<tree editable="top"><control>' +
        '<create string="Add a product"/>' +
        '<create string="Add a section" context="{\'default_display_type\': \'line_section\'}"/>' +
        '<create string="Add a note" context="{\'default_display_type\': \'line_note\'}"/>' +
        '</control>' +
        '<field name="product_id" widget="product_configurator" />' +
        '</tree>' +
        '</field>' +
        '</sheet>' +
        '</form>';
    };

    QUnit.module('Event Configurator', {
        beforeEach: function () {
            this.data = {
                'product.product': {
                    fields: {
                        id: {type: 'integer'},
                        detailed_type: {type: 'selection'},
                        rent_ok: {type: 'boolean'}//sale_rental purposes
                    },
                    records: [{
                        id: 1,
                        display_name: "Customizable Event",
                        detailed_type: 'event',
                        rent_ok: false//sale_rental purposes
                    }, {
                        id: 2,
                        display_name: "Desk",
                        detailed_type: 'service',
                        rent_ok: false//sale_rental purposes
                    }]
                },
                sale_order: {
                    fields: {
                        id: {type: 'integer'},
                        sale_order_line: {
                            string: 'lines',
                            type: 'one2many',
                            relation: 'sale_order_line'
                        },
                    }
                },
                sale_order_line: {
                    fields: {
                        product_id: {
                            string: 'product',
                            type: 'many2one',
                            relation: 'product.product'
                        },
                        event_ok: {type: 'boolean'},
                        rent_ok: {type: 'boolean'},//sale_rental purposes
                        event_id: {
                            string: 'event',
                            type: 'many2one',
                            relation: 'event'
                        },
                        event_ticket_id: {
                            string: 'event_ticket',
                            type: 'many2one',
                            relation: 'event_ticket'
                        }
                    }
                }
            };
        }
    }, function (){
        QUnit.test('Select a regular product and verify that the event configurator is not opened', async function (assert) {
            assert.expect(2);

            var form = await createView({
                View: FormView,
                model: 'sale_order',
                data: this.data,
                arch: getArch(),
                mockRPC: function (route, params) {
                    if (params.method === 'read' && params.args[1][0] === 'detailed_type') {
                        assert.ok(true);
                        return Promise.resolve([{detailed_type: 'service'}]);
                    }
                    return this._super.apply(this, arguments);
                },
                intercepts: {
                    do_action: function (ev) {
                        if (ev.data.action === 'event_sale.event_configurator_action') {
                            assert.ok(false, "Should not execute the configure action");
                        }
                    },
                }
            });

            await testUtils.dom.click(form.$("a:contains('Add a product')"));
            await testUtils.fields.many2one.searchAndClickItem("product_id", {item: 'Desk'})
            form.destroy();
        });

        QUnit.test('Select a configurable event and verify that the event configurator is opened', async function (assert) {
            assert.expect(2);

            var form = await createView({
                View: FormView,
                model: 'sale_order',
                data: this.data,
                arch: getArch(),
                mockRPC: function (route, params) {
                    if (params.method === 'read' && params.args[1][0] === 'detailed_type') {
                        assert.ok(true);
                        return Promise.resolve([{detailed_type: 'event'}]);
                    }
                    return this._super.apply(this, arguments);
                },
                intercepts: {
                    do_action: function (ev) {
                        if (ev.data.action === 'event_sale.event_configurator_action') {
                            assert.ok(true);
                        }
                    },
                }
            });

            await testUtils.dom.click(form.$("a:contains('Add a product')"));
            await testUtils.fields.many2one.searchAndClickItem("product_id", {item: 'Customizable Event'});
            form.destroy();
        });
    });
});
