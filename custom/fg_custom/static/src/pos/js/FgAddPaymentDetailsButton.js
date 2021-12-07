odoo.define('fg_custom.FgAddPaymentDetailsButton', function (require) {
   'use strict';
   const { Gui } = require('point_of_sale.Gui');
   const PosComponent = require('point_of_sale.PosComponent');
   const { posbus } = require('point_of_sale.utils');
   const ProductScreen = require('point_of_sale.ProductScreen');
   const { useListener } = require('web.custom_hooks');
   const Registries = require('point_of_sale.Registries');
   const PaymentScreen = require('point_of_sale.PaymentScreen');
   const PaymentMethodButton = require('point_of_sale.PaymentMethodButton');
   const models = require('point_of_sale.models');

   const AddCheckDetailsButton = (PaymentMethodButton) =>
       class extends PaymentMethodButton {
           constructor() {
               super(...arguments);
           }

          async AddCheckDetails() {
                this.trigger('new-payment-line', this.props.paymentMethod)
                var popupTitle = "Check Details"
                var currentOrder = this.env.pos.get_order();this.env.pos.get_order();
                if(currentOrder.selected_paymentline){
                    if(currentOrder.selected_paymentline.name == 'Check'){
                        const { confirmed, payload } = await this.showPopup('FgCheckDetailsPopup');
                        if (!confirmed) {
                            this.trigger('delete-payment-line', { cid: currentOrder.selected_paymentline.cid })
                            return;
                        };
                        const { x_check_number, x_issuing_bank, x_check_date } = payload;
                        currentOrder.selected_paymentline.x_check_number = x_check_number;
                        currentOrder.selected_paymentline.x_issuing_bank = x_issuing_bank;
                        currentOrder.selected_paymentline.x_check_date = x_check_date;
                        currentOrder.trigger('change', currentOrder); // needed so that export_to_JSON gets triggered
                        this.render();
                    }else{
                        Gui.showPopup("ErrorPopup", {
                           title: this.env._t(popupTitle),
                           body: this.env._t('Selected payment should be Check'),
                       });
                    }
                }else{
                    Gui.showPopup("ErrorPopup", {
                       title: this.env._t(popupTitle),
                       body: this.env._t('No selected payment.'),
                   });
                }
           }

           async AddGiftCardDetails() {
                this.trigger('new-payment-line', this.props.paymentMethod)
                var popupTitle = "Gift Card Details"
                var currentOrder = this.env.pos.get_order();this.env.pos.get_order();
                if(currentOrder.selected_paymentline){
                    if(currentOrder.selected_paymentline.name == 'Gift Card'){
                        const { confirmed, payload } = await this.showPopup('FgGiftCardDetailsPopup');
                        if (!confirmed) {
                            this.trigger('delete-payment-line', { cid: currentOrder.selected_paymentline.cid })
                            return;
                        };
                        const { x_gift_card_number} = payload;
                        currentOrder.selected_paymentline.x_gift_card_number = x_gift_card_number;
                        currentOrder.trigger('change', currentOrder); // needed so that export_to_JSON gets triggered
                        this.render();
                    }else{
                        Gui.showPopup("ErrorPopup", {
                           title: this.env._t(popupTitle),
                           body: this.env._t('Selected payment should be Gift Card'),
                       });
                    }
                }else{
                    Gui.showPopup("ErrorPopup", {
                       title: this.env._t(popupTitle),
                       body: this.env._t('No selected payment.'),
                   });
                }
           }


           async AddCardDetails() {
                this.trigger('new-payment-line', this.props.paymentMethod)
                var popupTitle = "Card Details"
                var currentOrder = this.env.pos.get_order();this.env.pos.get_order();
                if(currentOrder.selected_paymentline){
                    if(currentOrder.selected_paymentline.name == 'Debit Card' || currentOrder.selected_paymentline.name == 'Credit Card'){
                        const { confirmed, payload } = await this.showPopup('FgCardDetailsPopup');
                        if (!confirmed) {
                            this.trigger('delete-payment-line', { cid: currentOrder.selected_paymentline.cid })
                            return;
                        };
                        const { x_card_number, x_card_name, cardholder_name, x_approval_no, x_batch_num  } = payload;
                        currentOrder.selected_paymentline.x_card_number = x_card_number;
                        currentOrder.selected_paymentline.x_card_name = x_card_name;
                        currentOrder.selected_paymentline.cardholder_name = cardholder_name;
                        currentOrder.selected_paymentline.x_approval_no = x_approval_no;
                        currentOrder.selected_paymentline.x_batch_num = x_batch_num;
                        currentOrder.trigger('change', currentOrder); // needed so that export_to_JSON gets triggered
                        this.render();
                    }else{
                        Gui.showPopup("ErrorPopup", {
                           title: this.env._t(popupTitle),
                           body: this.env._t('Selected payment should be Debit/Credit Card'),
                       });
                    }
                }else{
                    Gui.showPopup("ErrorPopup", {
                       title: this.env._t(popupTitle),
                       body: this.env._t('No selected payment.'),
                   });
                }
           }

           async AddGCashDetails() {
                this.trigger('new-payment-line', this.props.paymentMethod)
                var popupTitle = "GCash Details"
                var currentOrder = this.env.pos.get_order();this.env.pos.get_order();
                if(currentOrder.selected_paymentline){
                    if(currentOrder.selected_paymentline.name == 'GCash'){
                        const { confirmed, payload } = await this.showPopup('FgGCashDetailsPopup');
                        if (!confirmed) {
                            this.trigger('delete-payment-line', { cid: currentOrder.selected_paymentline.cid })
                            return;
                        };
                        const { x_gcash_refnum, x_gcash_customer} = payload;
                        currentOrder.selected_paymentline.x_gcash_refnum = x_gcash_refnum;
                        currentOrder.selected_paymentline.x_gcash_customer = x_gcash_customer;
                        currentOrder.trigger('change', currentOrder); // needed so that export_to_JSON gets triggered
                        this.render();
                    }else{
                        Gui.showPopup("ErrorPopup", {
                           title: this.env._t(popupTitle),
                           body: this.env._t('Selected payment should be GCash'),
                       });
                    }
                }else{
                    Gui.showPopup("ErrorPopup", {
                       title: this.env._t(popupTitle),
                       body: this.env._t('No selected payment.'),
                   });
                }
           }

           async AddGiftCheckDetails() {
                this.trigger('new-payment-line', this.props.paymentMethod)
                var popupTitle = "Gift Check Details"
                var currentOrder = this.env.pos.get_order();this.env.pos.get_order();
                if(currentOrder.selected_paymentline){
                    if(currentOrder.selected_paymentline.name == 'Gift Check'){
                        const { confirmed, payload } = await this.showPopup('FgGiftCheckDetailsPopup');
                        if (!confirmed) {
                            this.trigger('delete-payment-line', { cid: currentOrder.selected_paymentline.cid })
                            return;
                        };
                        const { x_gc_voucher_no, x_gc_voucher_name, x_gc_voucher_cust } = payload;
                        currentOrder.selected_paymentline.x_gc_voucher_no = x_gc_voucher_no;
                        currentOrder.selected_paymentline.x_gc_voucher_name = x_gc_voucher_name;
                        currentOrder.selected_paymentline.x_gc_voucher_cust = x_gc_voucher_cust;
                        currentOrder.trigger('change', currentOrder); // needed so that export_to_JSON gets triggered
                        this.render();
                    }else{
                        Gui.showPopup("ErrorPopup", {
                           title: this.env._t(popupTitle),
                           body: this.env._t('Selected payment should be Gift Check'),
                       });
                    }
                }else{
                    Gui.showPopup("ErrorPopup", {
                       title: this.env._t(popupTitle),
                       body: this.env._t('No selected payment.'),
                   });
                }
           }

       };
   Registries.Component.extend(PaymentMethodButton, AddCheckDetailsButton);

   return AddCheckDetailsButton;
});

