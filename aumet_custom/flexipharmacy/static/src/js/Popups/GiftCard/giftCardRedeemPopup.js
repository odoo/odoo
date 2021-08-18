odoo.define('flexipharmacy.giftCardRedeemPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;

    class giftCardRedeemPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({ CardNumberLabel:'', CardSetCustomer:'', GiftCardNumber: ''});
            this.gift_card_number_ref = useRef('gift_card_number');
            this.gift_card_amount_ref = useRef('gift_card_amount');
            this.redeem = false;
        }
        mounted() {
            this.gift_card_number_ref.el.focus();
        }
        getPayload() {
            return {
                card_no: this.state.GiftCardNumber,
                card_amount: Number(this.state.GiftCardAmount),
                redeem: this.redeem,
            };
        }
        async confirm(){
            var self = this;
            var today = moment().locale('en').format('YYYY-MM-DD');
            var code = this.state.GiftCardNumber;
            var get_redeems = this.env.pos.get_order().get_redeem_giftcard();
            var existing_card = _.where(get_redeems, {'redeem_card': code });
            var gift_card = await rpc.query({
                model: 'aspl.gift.card',
                method: 'search_read',
                domain: [['card_no', '=', code], ['expire_date', '>=', today],['issue_date', '<=', today]],
            }, {async: false}).then(function(res){
                return res
            });
            if (gift_card && gift_card[0]){
                if (this.state.GiftCardAmount > gift_card[0].card_value){
                    $('#text_redeem_amount').focus();
                    this.state.CardNumberLabel = ""
                    this.state.CardSetCustomer = 'Please enter amount below card value.'
                }
                else if (this.state.GiftCardAmount > self.env.pos.get_order().get_due()){
                    $('#text_redeem_amount').focus();
                    this.state.CardNumberLabel = ""
                    this.state.CardSetCustomer = 'Please enter valid amount.'
                }else{
                    this.props.resolve({ confirmed: true, payload: await this.getPayload() });       
                }
            }
        }
        CheckGiftCardBalance() {
            self = this;
            var today = moment().locale('en').format('YYYY-MM-DD');
            var code = this.state.GiftCardNumber;
            var get_redeems = this.env.pos.get_order().get_redeem_giftcard();
            var existing_card = _.where(get_redeems, {'redeem_card': code });
            var params = {
                model: 'aspl.gift.card',
                method: 'search_read',
                domain: [['card_no', '=', code], ['expire_date', '>=', today],['issue_date', '<=', today]],
            }
            rpc.query(params, {async: false}).then(function(res){
                if(res.length > 0){
                    if (res[0]){
                        if(existing_card.length > 0){
                            res[0]['card_value'] = existing_card[existing_card.length - 1]['redeem_remaining']
                        }
                        self.redeem = res[0];
                        self.state.CardNumberLabel = "Your Balance is  "+ self.env.pos.format_currency(res[0].card_value)
                        if(res[0].customer_id[1]){
                            self.state.CardSetCustomer = "Hello  "+ res[0].customer_id[1]
                        } else{
                            self.state.CardSetCustomer = "Hello  "
                        }
                        $('#text_redeem_amount').show();
                        if(res[0].card_value <= 0){
                            $('#redeem_amount_row').hide();
                            $('#in_balance').show();
                        }else{
                            $('#redeem_amount_row').fadeIn('fast');
                            $('#text_redeem_amount').focus();
                        }

                        if (self.env.pos.get_order().get_due() < res[0].card_value){
                            self.state.GiftCardAmount = self.env.pos.get_order().get_due()
                        }
                        if (res[0].card_value < self.env.pos.get_order().get_due()){
                            self.state.GiftCardAmount = res[0].card_value
                        }
                    }
                }else{
                    $('#text_gift_card_no').focus();
                    self.state.CardNumberLabel = "";
                    self.state.CardSetCustomer = 'Barcode not found or gift card has been expired.' 
                    $('#text_redeem_amount').hide();
                }
            });
            
        }
        CheckGiftCardBalancekey(e) {
            if (e.which == 13 && this.state.GiftCardNumber) {
                this.CheckGiftCardBalance()
            }
        }
        cancel() {
            this.trigger('close-popup');
        }
    }
    giftCardRedeemPopup.template = 'giftCardRedeemPopup';

    giftCardRedeemPopup.defaultProps = {
        confirmText: 'Apply',
        cancelText: 'Cancel',
        title: '',
        body: '',
    };

    Registries.Component.add(giftCardRedeemPopup);

    return giftCardRedeemPopup;
});
