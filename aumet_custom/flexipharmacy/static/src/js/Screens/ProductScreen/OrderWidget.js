odoo.define('pos_serial.OrderWidgetInh', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const OrderWidget = require('point_of_sale.OrderWidget');
    const Registries = require('point_of_sale.Registries');
    const { useRef, useState } = owl.hooks;
    const { isRpcError } = require('point_of_sale.utils');
    var rpc = require('web.rpc');

    const OrderWidgetInh = (OrderWidget) =>
        class extends OrderWidget {
            constructor(){
                super(...arguments);
                this.state.serials = [];
            }
            async _editPackLotLines(event) {
                var self = this;
                if(this.env.pos.config.enable_pos_serial){
                    const orderline = event.detail.orderline;
                    const isAllowOnlyOneLot = orderline.product.isAllowOnlyOneLot();
                    const packLotLinesToEdit = orderline.getPackLotLinesToEdit(isAllowOnlyOneLot);
                    var product_id = orderline.product
                    var picking_type = this.env.pos.config.picking_type_id[0]
                    var params = {
                        model: 'stock.production.lot',
                        method: 'product_lot_and_serial',
                        args: [product_id, product_id.id, picking_type]
                    }
                    try {
                        await rpc.query(params).then(async function(serials){
                            if(serials){
                                 for(var i=0 ; i < serials.length ; i++){
                                     if(serials[i].remaining_qty > 0){
                                        serials[i]['isSelected'] = false;
                                        serials[i]['inputQty'] = 1;
                                        if(serials[i].expiration_date){
                                            let localTime =  moment.utc(serials[i].expiration_date).toDate();
                                            serials[i]['expiration_date'] = moment(localTime).format('YYYY-MM-DD hh:mm A');
                                        }
                                        if(self.env.pos.config.product_exp_days){
                                             let product_exp_date = moment().add(self.env.pos.config.product_exp_days, 'd')
                                                                    .format('YYYY-MM-DD');
                                             let serial_life = moment(serials[i]['expiration_date']).format('YYYY-MM-DD');
                                             if(product_exp_date >= serial_life){
                                                serials[i]['NearToExpire'] = 'NearToExpire';
                                             }
                                        }
                                        self.state.serials.push(serials[i])
                                     }
                                 }
                                self.state.serials.sort(function(a,b){
                                    return (b.expiration_date) - (a.expiration_date);
                                });
                                self.showScreen('PackLotLineScreen', {isSingleItem : isAllowOnlyOneLot,
                                                                       orderline : orderline,
                                                                       serials : self.state.serials});
                            }
                        });
                    }catch (error) {
                        if (isRpcError(error) && error.message.code < 0) {
                            self.env.pos.get_order().set_connected(false)
                            super._editPackLotLines(event);
                        } else {
                            return;
                        }
                    } 
                }else{
                    super._editPackLotLines(event);
                }
            }

        }

    Registries.Component.extend(OrderWidget, OrderWidgetInh);

    return OrderWidgetInh;

});
