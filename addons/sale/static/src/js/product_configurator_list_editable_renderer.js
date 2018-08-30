/**
 * This adds the possibility to open the product configurator when the control
 * "Configure a product" is clicked
 */
odoo.define('sale.ProductConfiguratorEditableListRenderer', function (require) {
    "use strict";

    var core = require('web.core');
    var _t = core._t;
    var ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        /**
         * @override
         */
        _onAddRecord: function (ev) {
            // we don't want the browser to navigate to a the # url
            ev.preventDefault();

            // we don't want the click to cause other effects, such as unselecting
            // the row that we are creating, because it counts as a click on a tr
            ev.stopPropagation();

            // but we do want to unselect current row
            var self = this;
            this.unselectRow().then(function () {
                var open_product_configurator = false;
                var context = ev.currentTarget.dataset.context;

                var context_json = false;
                if(context){
                    context = context.replace(/\'/g, '"');
                    context_json = JSON.parse(context);
    
                    open_product_configurator = context_json.open_product_configurator;
                }

                if(open_product_configurator){
                    self._rpc({
                        model: 'ir.model.data',
                        method: 'xmlid_to_res_id',
                        kwargs: {xmlid: 'sale.sale_product_configurator_view_form'},
                    }).then(function(res_id) {
                        self.do_action({
                            name: _t('Configure a product'),
                            type: 'ir.actions.act_window',
                            res_model: 'sale.product.configurator',
                            views: [[res_id, 'form']],
                            target: 'new'
                        }, {
                            on_close: function (products) {
                                if(products && products != 'special'){
                                    self.trigger_up('add_record', {
                                        context: products,
                                        forceEditable: "bottom" ,
                                        allowWarning: true,
                                        onSuccess: function(){
                                            self.unselectRow();
                                        }
                                    });
                                }
                            }
                        });
                    });
                } else {
                    self.trigger_up('add_record', {context: context && [context]}); // TODO write a test, the deferred was not considered
                }
            });
        }
    });
});