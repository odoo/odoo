odoo.define('flexipharmacy.MiddleCustomControlButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { Gui } = require('point_of_sale.Gui');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const { useRef, useState } = owl.hooks;
    const { isRpcError } = require('point_of_sale.utils');

    var rpc = require('web.rpc');

    class MiddleCustomControlButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('empty-cart', this.EmptyCartButtonClick);
            useListener('show-warehouse', this.ShowWarehouseQty);
            useListener('create-internal-transfer', this.CreateInternalTransfer);
            useListener('add_wallet_amount', this.AddWalletAmount);
            useListener('open-gift-card-screen', this.OpenGiftCardScreen);
            useListener('open-gift-voucher-screen', this.OpenGiftVoucherScreen);
            useListener('apply-bag-charges', this.ApplyBagCharges);
            useListener('create-money-in-out', this.CreateMoneyInOut);
            useListener('open-purchase-history-popup', this.OpenPurchaseHistoryPopup);
            useListener('show-multi-shop-option', this.ShowWarehouseQty);
            useListener('show-order-return-screen', this.ShowOrderReturnScreen);
            useListener('show-order-note-popup', this.ShowOrderNotePopup);
            useListener('show-alternative-product', this.ShowAlternativeProduct);
            useListener('show-cross-selling-product', this.ShowCrossSellingProduct);
            useListener('add-delivery-charge', this.AddDeliveryCharge);
            useListener('show-material-monitor', this.ShowMaterialMonitorScreen);
            this.state = useState({'is_packaging_filter': false})
        }
        async connectionCheck(){
            var self = this;
            try {
                await rpc.query({
                    model: 'pos.session',
                    method: 'connection_check',
                    args: [this.env.pos.pos_session.id],
                });
                self.state.is_connected = true
                self.env.pos.get_order().set_connected(true)
            } catch (error) {
                if (isRpcError(error) && error.message.code < 0) {
                    self.env.pos.get_order().set_connected(false)
                    self.state.is_connected = false
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Cannot access order management screen if offline.'),
                    });
                } else {
                    throw error;
                }
            }            
        }
        orderIsEmpty(order) {
            var self = this;
            var currentOrderLines = order.get_orderlines();
            var lines_ids = []
            if(!order.is_empty()) {
                _.each(currentOrderLines,function(item) {
                    lines_ids.push(item.id);
                });
                _.each(lines_ids,function(id) {
                    order.remove_orderline(order.get_orderline(id));
                });
            }
        }
        async ShowOrderNotePopup(){
            const { confirmed, payload: inputNote } = await this.showPopup('ProductNotePopup', {
                startingValue: this.env.pos.get_order().get_order_note(),
                title: this.env._t('Order Note'),
            });

            if (confirmed) {
                var order = this.env.pos.get_order();
                this.env.pos.get_order().set_order_note(inputNote);
                if(this.env.pos.config.customer_display){
                    order.mirror_image_data();
                }
            }
        }
        async EmptyCartButtonClick(){
            var self = this;
            var order = self.env.pos.get_order();
            var lines = order.get_orderlines();
            if(lines.length > 0){
                const { confirmed } = await this.showPopup('ConfirmPopup', {
                    title: 'Empty Cart ?',
                    body: 'You will lose all items associated with the current order',
                });
                if (confirmed) {
                    self.orderIsEmpty(order);
                    if(self.env.pos.config.customer_display){
                        order.mirror_image_data();
                    }
                }
            }
        }
        // if AddDeliveryCharge is enable
        async AddDeliveryCharge(){
            await this.connectionCheck()
            if (this.env.pos.get_order().get_connected()){
                const { confirmed, payload: DeliveryData } = await this.showPopup('DeliveryChargePopup', {
                    title: this.env._t('Delivery Detail'),
                    address: this.env.pos.get_order().get_client() ? this.env.pos.get_order().get_client().address : '', 
                    data: this.env.pos.get_order().get_delivery_charge_data()
                });
                if (confirmed){
                    this.env.pos.get_order().set_delivery_charge(this.env.pos.config.delivery_product_amount)
                    this.env.pos.get_order().set_delivery_charge_data(DeliveryData)
                    
                }
            }
        }
        // if Display Stock is enable
        async ShowWarehouseQty(){
            await this.connectionCheck()
            if (this.env.pos.get_order().get_connected()){
                this.trigger('button-click');
            }
        }
        // if Internal Stock Transfer is enable
        async CreateInternalTransfer(){
            var self = this
            await this.connectionCheck()
            if (this.env.pos.get_order().get_connected()){
                var selectedOrder = this.env.pos.get_order();
                var currentOrderLines = selectedOrder.get_orderlines();
                let flag;
                _.each(currentOrderLines,function(item) {
                    if(item.product.type === "product"){
                        flag = true;
                        return;
                    }
                });
                if(!flag){
                    alert("No Storable Product Found!");
                    return;
                }
                const { confirmed, payload: popup_data} = await this.showPopup('internalTransferPopup',
                                                                                {title: this.env._t('Internal Transfer')});
                if (confirmed){
                    var moveLines = [];
                    _.each(currentOrderLines,function(item) {
                        if(item.product.type === "product"){
                            let product_name = item.product.default_code ?
                                        "["+ item.product.default_code +"]"+ item.product.display_name :
                                        item.product.display_name;

                            moveLines.push({
                                'product_id': item.product.id,
                                'name': product_name,
                                'product_uom_qty': item.quantity,
                                'location_id': Number(popup_data.SourceLocation),
                                'location_dest_id': Number(popup_data.DestLocation),
                                'product_uom': item.product.uom_id[0],
                            });
                        }
                    });

                    var move_vals = {
                        'picking_type_id': Number(popup_data.PickingType),
                        'location_src_id':  Number(popup_data.SourceLocation),
                        'location_dest_id': Number(popup_data.DestLocation),
                        'state': popup_data.stateOfPicking,
                        'moveLines': moveLines,
                    }
                    await rpc.query({
                        model: 'stock.picking',
                        method: 'internal_transfer',
                        args: [move_vals],
                    }).then(function (result) {
                        if(result && result[0] && result[0]){
                            var url = window.location.origin + '/web#id=' + result[0] + '&view_type=form&model=stock.picking';
                            const { confirmed, payload} = self.showPopup('PurchaseOrderCreate', {
                                title: self.env._t('Confirmation'),
                                SelectedProductList:[],
                                defination: 'Internal Transfer Created',
                                CreatedPurchaseOrder:'True',
                                CreatedInternalTransfer:'True',
                                order_name:result[1],
                                order_id:result[0],
                                url:url,
                            });
                            self.selectedProductList = [];
                        }
                    });
                }
            }
        }
        // if Wallet is enable
        async AddWalletAmount(){
            await this.connectionCheck()
            if (this.env.pos.get_order().get_connected()){
                if(this.env.pos.get_order().get_client()){
                    const { confirmed,payload } = await this.showPopup('WalletPopup', {
                        title: this.env._t('Add to Wallet'),
                        customer: this.env.pos.get_order().get_client().name,
                    });
                    if (confirmed) {
                        if(this.env.pos.get_order().get_orderlines().length > 0){
                            const { confirmed } = await this.showPopup('ConfirmPopup', {
                                title: this.env._t('would you like to discard this order?'),
                                body: this.env._t(
                                    'If you want to recharge wallet then you have to discard this order'
                                ),
                            });
                            if (confirmed) {
                                this.orderIsEmpty(this.env.pos.get_order());
                            }
                        }
                        var product_id = this.env.pos.config.wallet_product[0]
                        var product = this.env.pos.db.get_product_by_id(product_id)
                        var amount = payload["amount"]
                        this.env.pos.get_order().set_is_rounding(false)
                        this.env.pos.get_order().set_type_for_wallet('change');
                        this.env.pos.get_order().add_product(product, {
                            price: amount,
                            extras: {
                                price_manually_set: true,
                            },
                        });
                        this.showScreen('PaymentScreen');
                    }
                }
            }
        }
        // if Gift Card is enable
        async OpenGiftCardScreen(){
            await this.connectionCheck()
            if (this.env.pos.get_order().get_connected()){
                this.showScreen('GiftCardScreen');
            }
        }
        // if Gift Voucher is enable
        async OpenGiftVoucherScreen(){
            await this.connectionCheck()
            if (this.env.pos.get_order().get_connected()){
                this.showScreen('GiftVoucherScreen');
            }
        }
        // if Gift Voucher is enable
        ApplyBagCharges(){
            var product_dict = this.env.pos.db.product_by_id
            var product_by_id = _.filter(product_dict, function(product){
                return product.is_packaging;
            });
            this.state.is_packaging_filter = !this.state.is_packaging_filter
            this.trigger('is_packaging', product_by_id);
        }
        // if Money In/Out is enable
        async CreateMoneyInOut(event){
            await this.connectionCheck()
            if (this.env.pos.get_order().get_connected()){
                const { confirmed, payload} = await this.showPopup('MoneyInOutPopup', {
                    title: this.env._t(event.detail.title),
                    type: event.detail.type,
                });
                if(confirmed){
                    try {
                        if(!this.env.pos.config.cash_control){
                            this.env.pos.db.notification('danger',this.env._t("Please enable cash control from point of sale settings."));
                            return;
                        }
                        await this.rpc({
                            model: 'pos.session',
                            method: 'take_money_in_out',
                            args: [[this.env.pos.pos_session.id], payload],
                        });
                        if (this.env.pos.config.money_in_out_receipt){
                            var use_posbox = this.env.pos.config.is_posbox && (this.env.pos.config.iface_print_via_proxy);
                            if (use_posbox || this.env.pos.config.other_devices) {
                                const report = this.env.qweb.renderToString('MoneyInOutReceipt',{props: {'check':'from_money_in_out', 'type': payload.type, 'InOutDetail': payload, 'company':this.env.pos.company, 'pos': this.env.pos, 'session':this.env.pos.session, 'date': moment().format('LL')}});
                                const printResult = await this.env.pos.proxy.printer.print_receipt(report);
                                if (!printResult.successful) {
                                    await this.showPopup('ErrorPopup', {
                                        title: printResult.message.title,
                                        body: printResult.message.body,
                                    });
                                } 
                                this.trigger('close-popup');
                            } else {
                                this.showScreen('ReceiptScreen', {'check':'from_money_in_out', 'type': payload.type, 'InOutDetail': payload, 'company':this.env.pos.company, 'session':this.env.pos.session, 'date': moment().format('LL')});
                                this.trigger('close-popup');
                            }
                        }
                    } catch (error) {
                        if (error.message.code < 0) {
                            await this.showPopup('OfflineErrorPopup', {
                                title: this.env._t('Offline'),
                                body: this.env._t('Unable to change background color'),
                            });
                        } else {
                            throw error;
                        }
                    }
                }
            }
        }
        async OpenPurchaseHistoryPopup(){
            var self = this
            await this.connectionCheck()
            if (this.env.pos.get_order().get_connected()){
                var product_ids = [];
                var order_line = this.env.pos.get_order().get_orderlines()
                var partner_id = this.env.pos.get_order().get_client().id
                if (order_line && order_line.length > 0) {
                    order_line = _.each(order_line, function (each) {
                        product_ids.push(each.product.id);
                    });
                    rpc.query({
                            model: 'pos.order',
                            method: 'get_all_product_history',
                            args: [product_ids, partner_id],
                        }, {
                            async: true
                        }).then(async function (res) {
                            const { confirmed, payload: popup_data} = await self.showPopup('PurchaseHistoryPopup', {
                                last_purchase_history: res.res_last_purchase_history,  
                                product_history:res.res_product_history,
                                last_order_date:res.date_order,
                                last_order_name:res.order_name,
                            }); 
                            
                    });
                }
            }
        }
        async ShowOrderReturnScreen(){
            await this.connectionCheck()
            if (this.env.pos.get_order().get_connected()){
                this.showScreen('OrderReturnScreen');
            }
        }
        ShowAlternativeProduct(){
            this.trigger('Click-Alternate-Product');
        }
        ShowCrossSellingProduct(){
            this.trigger('Cross-Selling-Product');
        }
        ShowMaterialMonitorScreen(){
            this.showScreen('MaterialMonitorScreen');
        }
    }
    MiddleCustomControlButton.template = 'MiddleCustomControlButton';

    Registries.Component.add(MiddleCustomControlButton);

    return MiddleCustomControlButton;
});
 