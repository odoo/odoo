/** @odoo-module */
import FormView from 'web.FormView';
import testUtils from 'web.test_utils';
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { ProductConfiguratorWidget } from "@sale_product_configurator/js/product_configurator_widget";
const createView = testUtils.createView;

const getArch = function (){
    return '<form>' +
    '<sheet>' +
    '<field name="pricelist_id" widget="selection" />' +
    '<field name="sale_order_line" widget="section_and_note_one2many">' +
    '<tree editable="top"><control>' +
    '<create string="Add a product"/>' +
    '<create string="Add a section" context="{\'default_display_type\': \'line_section\'}"/>' +
    '<create string="Add a note" context="{\'default_display_type\': \'line_note\'}"/>' +
    '</control>' +
    '<field name="product_id" invisible="1"/>' +
    '<field name="product_template_id" widget="product_configurator"/>' +
    '<field name="product_uom_qty"/>' +
    '<field name="product_custom_attribute_value_ids" invisible="1"/>' +
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
                    product_template_id: {
                        string: 'product template',
                        type: 'many2one',
                        relation: 'product_template'
                    },
                    product_id: {
                        string: 'product',
                        type: 'many2one',
                        relation: 'product'
                    },
                    product_custom_attribute_value_ids: {
                        string: 'product_custom_attribute_values',
                        type: 'one2many',
                        relation: 'product_custom_attribute_value'
                    },
                    product_uom_qty: {type: 'integer'},
                    sequence: {type: 'integer'},
                }
            },
            product_custom_attribute_value: {
                fields: {
                    id: {type: 'integer'},
                    sale_order_line_id: {
                        string: 'sale order line',
                        type: 'many2one',
                        relation: 'sale_order_line'
                    }
                }
            },
            sale_product_configurator: {
                fields: {
                    product_template_id: {
                        string: 'product',
                        type: 'many2one',
                        relation: 'product_template'
                    },
                    product_template_attribute_value_ids: {
                        type: 'many2many',
                        relation: 'product_template_attribute_value'
                    },
                    product_no_variant_attribute_value_ids: {
                        type: 'many2many',
                        relation: 'product_template_attribute_value'
                    },
                    product_custom_attribute_value_ids: {
                        type: 'many2many',
                        relation: 'product_attribute_custom_value'
                    }
                },
                records: [{
                    product_template_id: 42
                }]
            },
            product_template_attribute_value: {
                fields: {
                    id: {type: 'integer'}
                }
            },
            product_attribute_custom_value: {
                fields: {
                    id: {type: 'integer'}
                }
            },
            pricelist: {
                fields: {
                    id: {type: 'integer'}
                }
            }
        };
    }
}, function () {
    QUnit.test('Select a non configurable product template and verify that the product_id is correctly set', async function (assert) {
        assert.expect(2);

        const form = await createView({
            View: FormView,
            model: 'sale_order',
            data: this.data,
            arch: getArch(),
            mockRPC: function (route, params) {
                if (params.method === 'get_single_product_variant') {
                    assert.ok(true);
                    return Promise.resolve({product_id: 2});
                }
                // FIXME awa: this shouldn't be here since the read is done in 'event_sale'
                // But at the moment there is no easy way to solve such cross module 'include' issues
                if (params.method === 'read') {
                    return Promise.resolve(false);
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                do_action: function (ev) {
                    if (ev.data.action === 'sale_product_configurator.sale_product_configurator_action') {
                        assert.ok(false, "Should not execute the configure action");
                    }
                },
            }
        });

        await testUtils.dom.click(form.$("a:contains('Add a product')"));
        await testUtils.fields.many2one.searchAndClickItem("product_template_id", {item: 'Customizable Desk'});
        // check that product_id is correctly set to 2
        assert.strictEqual(form.renderer.state.data.sale_order_line.data[0].data.product_id.data.id, 2);
        form.destroy();
    });

    QUnit.test('Select a configurable product template and verify that the product configurator is opened', async function (assert) {
        patchWithCleanup(ProductConfiguratorWidget.prototype, {
            _openProductConfigurator() {
                assert.step("open configurator");
            }
        });
        const form = await createView({
            View: FormView,
            model: 'sale_order',
            data: this.data,
            arch: getArch(),
            mockRPC: function (route, params) {
                if (params.method === 'get_single_product_variant') {
                    assert.ok(true);
                    return Promise.resolve(false);
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(form.$("a:contains('Add a product')"));
        assert.verifySteps([]);
        await testUtils.fields.many2one.searchAndClickItem("product_template_id", {item: 'Customizable Desk'});
        assert.verifySteps(["open configurator"]);
        form.destroy();
    });

    QUnit.test('trigger_up the "add_record" event and checks that rows are correctly added to the list', async function (assert) {
        assert.expect(1);

        const form = await createView({
            View: FormView,
            model: 'sale_order',
            data: this.data,
            arch: getArch()
        });

        let list = form.renderer.allFieldWidgets[form.handle][1];

        list.trigger_up('add_record', {
            context: [{default_product_id: 1, default_product_uom_qty: 2}, {default_product_id: 2, default_product_uom_qty: 3}],
            forceEditable: "bottom" ,
            allowWarning: true
        });
        await testUtils.nextTick();

        assert.containsN(list, "tr.o_data_row", 2);
        form.destroy();
    });

    QUnit.test('drag and drop rows containing product_configurator many2one', async function (assert) {
        assert.expect(4);

        this.data.sale_order.records = [
            { id: 1, sale_order_line: [1, 2] }
        ];
        this.data.sale_order_line.records = [
            { id: 1, sequence: 5, product_id: 1 },
            { id: 2, sequence: 15, product_id: 2 },
        ];

        const form = await createView({
            View: FormView,
            model: 'sale_order',
            data: this.data,
            arch: `
                <form>
                    <field name="sale_order_line"/>
                </form>`,
            archs: {
                'sale_order_line,false,list': `
                    <tree editable="bottom">
                        <field name="sequence" widget="handle"/>
                        <field name="product_id" widget="product_configurator"/>
                    </tree>`,
            },
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.containsN(form, '.o_data_row', 2);
        assert.strictEqual(form.$('.o_data_row').text(), 'Customizable Desk (1)Customizable Desk (2)');
        assert.containsN(form, '.o_data_row .o_row_handle', 2);

        // move first row below second
        const $firstHandle = form.$('.o_data_row:nth(0) .o_row_handle');
        const $secondHandle = form.$('.o_data_row:nth(1) .o_row_handle');
        await testUtils.dom.dragAndDrop($firstHandle, $secondHandle, { position: 'bottom' });

        assert.strictEqual(form.$('.o_data_row').text(), 'Customizable Desk (2)Customizable Desk (1)');

        form.destroy();
    });
});
