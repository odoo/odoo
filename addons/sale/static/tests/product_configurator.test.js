odoo.define('sale.product.configurator.tests', function (require) {
    "use strict";
    
    var FormView = require('web.FormView');
    var ProductConfiguratorFormView = require('sale.ProductConfiguratorFormView');
    var testUtils = require('web.test_utils');
    var ajax = require('web.ajax');
    var createView = testUtils.createView;

    var getArch = function(){
        return '<form>' +
        '<sheet>' +
        '<field name="sale_order_line">' +
        '<tree editable="top"><control>' +
        '<create string="Add a product"/>' +
        '<create string="Configure a product" context="{\'open_product_configurator\': \'true\'}"/>' +
        '<create string="Add a section" context="{\'default_display_type\': \'line_section\'}"/>' +
        '<create string="Add a note" context="{\'default_display_type\': \'line_note\'}"/>' +
        '</control>' +
        '<field name="product_id"/><field name="quantity"/>' +
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
                    }
                },
                sale_order: {
                    fields: {
                        id: {type: 'integer'},
                        sale_order_line: {string: 'lines', type: 'one2many', relation: 'sale_order_line'},
                    }
                },
                sale_order_line: {
                    fields: {
                        product_id: {string: 'product', type: 'many2one', relation: 'product'},
                        quantity: {type: 'integer'}
                    }
                },
                sale_product_configurator: {
                    fields: {
                        product_template_id: {string: 'product', type: 'many2one', relation: 'product_template'}
                    },
                    records: [{
                        product_template_id: 42
                    }]
                },
            };
        }
    }, function(){
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

            var list = form.renderer.allFieldWidgets[form.handle][0];
    
            list.trigger_up('add_record', {
                context: [{product_id: 1, quantity: 2}, {product_id: 2, quantity: 3}],
                forceEditable: "bottom" ,
                allowWarning: true
            });

            assert.strictEqual(list.$("tr.o_data_row").length, 2);
        });

        QUnit.test('Select a product in the list and check for template loading', function(assert){
            assert.expect(1);

            ajax.jsonRpc = function(route){
                assert.ok(true);
                return $.Deferred().then(_.constant($("<div></div>")));
            };

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
            });
            var div = '<div>';
            var $div = $(div).addClass('js_sale_order_pricelist_id').html(43);
            product_configurator_form.$('.o_input').after($div);
            product_configurator_form.$('.o_input').click();
            $("ul.ui-autocomplete li a:contains('Customizable Desk')").mouseenter().click();
        });
    });
});
