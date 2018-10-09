odoo.define('sale.product.configurator.tests', function (require) {
    "use strict";

    var FormView = require('web.FormView');
    var ProductConfiguratorFormView = require('sale.ProductConfiguratorFormView');
    var testUtils = require('web.test_utils');
    var createView = testUtils.createView;

    var getArch = function (){
        return '<form>' +
        '<sheet>' +
        '<field name="pricelist_id" widget="selection" />' +
        '<field name="sale_order_line" widget="section_and_note_one2many">' +
        '<tree editable="top"><control>' +
        '<create string="Add a product"/>' +
        '<create string="Configure a product" context="{\'open_product_configurator\': True}"/>' +
        '<create string="Add a section" context="{\'default_display_type\': \'line_section\'}"/>' +
        '<create string="Add a note" context="{\'default_display_type\': \'line_note\'}"/>' +
        '</control>' +
        '<field name="product_id"/><field name="product_uom_qty"/>' +
        '</tree>' +
        '</field>' +
        '</sheet>' +
        '</form>';
    };

    QUnit.module('Product Configurator', {
        beforeEach: function () {
            this.data = {
                product_template: {
                    fields: {
                        id: {type: 'integer'}
                    },
                    records: [{
                        id: 42,
                        display_name: "Customizable Desk"
                    }]
                },
                product: {
                    fields: {
                        id: {type: 'integer'}
                    },
                    records: [{
                        id: 1,
                        display_name: "Customizable Desk (1)"
                    }, {
                        id: 2,
                        display_name: "Customizable Desk (2)"
                    }]
                },
                sale_order: {
                    fields: {
                        id: {type: 'integer'},
                        pricelist_id: {
                            string: 'Pricelist',
                            type: 'one2many',
                            relation: 'pricelist'
                        },
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
                            relation: 'product'
                        },
                        product_uom_qty: {type: 'integer'}
                    }
                },
                sale_product_configurator: {
                    fields: {
                        product_template_id: {
                            string: 'product',
                            type: 'many2one',
                            relation: 'product_template'
                        }
                    },
                    records: [{
                        product_template_id: 42
                    }]
                },
                pricelist: {
                    fields: {
                        id: {type: 'integer'}
                    }
                }
            };
        }
    }, function (){
        QUnit.test('click on "Configure a product" and check for form loading', function (assert) {
            assert.expect(2);

            var form = createView({
                View: FormView,
                model: 'sale_order',
                data: this.data,
                arch: getArch(),
                    mockRPC: function (route) {
                        if (route === '/web/dataset/call_kw/ir.model.data/xmlid_to_res_id') {
                            assert.ok(true);
                            return $.Deferred().then(_.constant(1));
                        }
                        return this._super.apply(this, arguments);
                    },
            });

            assert.strictEqual(form.$("a:contains('Configure a product')").length, 1);

            form.$("a:contains('Configure a product')").click();
        });

        QUnit.test('trigger_up the "add_record" event and checks that rows are correctly added to the list', function (assert) {
            assert.expect(1);

            var form = createView({
                View: FormView,
                model: 'sale_order',
                data: this.data,
                arch: getArch()
            });

            var list = form.renderer.allFieldWidgets[form.handle][1];

            list.trigger_up('add_record', {
                context: [{default_product_id: 1, default_product_uom_qty: 2}, {default_product_id: 2, default_product_uom_qty: 3}],
                forceEditable: "bottom" ,
                allowWarning: true
            });

            assert.strictEqual(list.$("tr.o_data_row").length, 2);
        });

        QUnit.test('Select a product in the list and check for template loading', function (assert){
            assert.expect(1);

            var product_configurator_form = createView({
                View: ProductConfiguratorFormView,
                model: 'sale_product_configurator',
                data: this.data,
                arch:
                    '<form js_class="product_configurator_form">' +
                        '<group>' +
                            '<field name="product_template_id" class="oe_product_configurator_product_template_id" />' +
                        '</group>' +
                        '<footer>' +
                            '<button string="Add" class="btn-primary o_sale_product_configurator_add disabled"/>' +
                            '<button string="Cancel" class="btn-secondary" special="cancel"/>' +
                        '</footer>' +
                    '</form>',
                    mockRPC: function (route) {
                        if (route === '/product_configurator/configure') {
                            assert.ok(true);
                            return $.Deferred().then(_.constant(1));
                        }
                        return this._super.apply(this, arguments);
                    }
            });
            product_configurator_form.$('.o_input').click();
            $("ul.ui-autocomplete li a:contains('Customizable Desk')").mouseenter().click();
        });
    });
});
