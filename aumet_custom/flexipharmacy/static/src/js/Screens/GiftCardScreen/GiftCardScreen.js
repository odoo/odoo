    odoo.define('point_of_sale.GiftCardScreen', function(require) {
    'use strict';

    const { debounce } = owl.utils;
    const { useState } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;

    class GiftCardScreen extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('close-screen', this.close);
            useListener('click-extend', () => this.extendExpireDate());
            useListener('click-recharge', () => this.rechargeGiftCard());
            useListener('click-exchange', () => this.ChangeCardGiftCard());
            useListener('search', this._onSearch);
            this.searchDetails = {};
            this.filter = null;
            this._initializeSearchFieldConstants();
            this.state = useState({
                query: null,
                selectedCard: this.props.gift_card,
                detailIsShown: false,
                isEditMode: false,
                editModeProps: {
                    partner: {
                        country_id: this.env.pos.company.country_id,
                        state_id: this.env.pos.company.state_id,
                    }
                },
            })
            this.updateClientList = debounce(this.updateClientList, 70);
        }
        async reloadNewGiftCard() {
            var self = this;
            var params = {
                model: 'aspl.gift.card',
                method: 'search_read',
                domain: [['is_active', '=', true]],
            }
            rpc.query(params, {async: false}).then(function(result){
                self.env.pos.set('gift_card_order_list', result);
                self.render()
            })
        }
        get_gift_cards(){
            return this.env.pos.get('gift_card_order_list');
        }
        close(){
            this.showScreen('ProductScreen');
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
        async ChangeCardGiftCard() {
            var self = this;
            const { confirmed, payload: selectedCard } = await this.showPopup('giftCardExchangePopup', {
                title: this.env._t('Exchange Gift Card'),
                selectedCard: this.state.selectedCard,
            }); 
            if(confirmed){
                var duplicate = false
                if(selectedCard.NewCardNumber && selectedCard.NewCardNumber > 0){
                    var card_number = selectedCard.NewCardNumber;
                    await this.rpc({
                        model: 'aspl.gift.card',
                        method: 'search_read',
                        domain: [['card_no', '=', card_number]],
                    }, {async: false}).then((gift_count) => {
                        if(gift_count && gift_count.length > 0){
                            self.env.pos.db.notification('danger',_t('Card already exist.'));
                            return
                        }
                    });
                    await this.rpc({
                        model: 'aspl.gift.card',
                        method: 'write_gift_card_from_ui',
                        args: [[Number(this.state.selectedCard.id)],selectedCard.NewCardNumber],
                    });
                    this.reloadNewGiftCard()
                    this.render();
                }else{
                    self.env.pos.db.notification('danger',_t('Enter gift card number.'));
                }
            }
        }
        async rechargeGiftCard(){
            const { confirmed, payload: selectedCard } = await this.showPopup('giftCardRechargePopup', {
                title: this.env._t('Recharge Card'),
                selectedCard: this.state.selectedCard,
            }); 
            if(confirmed){
                var self = this;
                var order = self.env.pos.get_order();
                var client = order.get_client();
                var card_details = this.state.selectedCard
                var set_customer = $('#set_customers').val();
                if(!client){
                    order.set_client(self.env.pos.db.get_partner_by_id(card_details.customer_id[0]));
                }
                var recharge_amount = selectedCard.amount
                if( 0 < Number(recharge_amount) ){
                    var vals = {
                        'recharge_card_id':card_details.id,
                        'recharge_card_no':card_details.card_no,
                        'recharge_card_amount':Number(recharge_amount),
                        'card_customer_id': card_details.customer_id[0] || false,
                        'customer_name': card_details.customer_id[1],
                        'total_card_amount':Number(recharge_amount)+card_details.card_value,
                    }
                    var get_recharge = order.get_recharge_giftcard();
                    var product = self.env.pos.db.get_product_by_id(self.env.pos.config.gift_card_product_id[0]);
                    if (self.env.pos.config.gift_card_product_id[0]){
                        var amount = recharge_amount
                        self.orderIsEmpty(self.env.pos.get_order());
                        this.env.pos.get_order().set_is_rounding(false)
                        this.env.pos.get_order().set_type_for_wallet('change');
                        this.env.pos.get_order().add_product(product, {
                            price: amount,
                            extras: {
                                price_manually_set: true,
                            },
                        });
                        order.set_recharge_giftcard(vals);
                        this.showScreen('PaymentScreen');
                    }
                }else{
                    self.env.pos.db.notification('danger',_t('Please enter valid amount.'));
                }
            }
        }
        async extendExpireDate() {
            var self = this;
            const { confirmed, payload: selectedCard } = await this.showPopup('giftCardEditExpirePopup', {
                title: this.env._t('Extend Expire Date'),
                selectedCard: this.state.selectedCard,
            }); 
            var card_id = this.state.selectedCard.id;
            if (confirmed) {
                if(selectedCard.new_expire_date){
                    if(this.state.selectedCard.card_no){
                        var EditCardPromise = new Promise(function(resolve, reject){
                            var params = {
                                model: "aspl.gift.card",
                                method: "write",
                                args: [card_id ,{'expire_date': moment(selectedCard.new_expire_date).format('YYYY-MM-DD')}]
                            }
                            rpc.query(params, {async: false}).then(function(result){
                                if(result){
                                    resolve(result);
                                    self.reloadNewGiftCard()
                                }
                            }).catch(function(){
                                reject(self.pos.db.notification('danger',"Connection lost"));
                            });
                        });
                    }else{
                        self.pos.db.notification('danger',_t('Please enter valid card no.'));
                    }
                }else{
                    self.pos.db.notification('danger',_t('Please select date.'));
                }
            }
        }
        get clients() {
            if (this.state.query && this.state.query.trim() !== '') {
                return this.env.pos.db.search_gift_card(this.state.query.trim());
            } 
        }
        updateClientList(event) {
            this.state.query = event.target.value;
            const clients = this.clients;
            if (event.code === 'Enter' && clients.length === 1) {
                this.state.selectedClient = clients[0];
                this.clickNext();
            } else {
                this.render();
            }
        }

        clickCard(event) {
            let card = event.detail.card;
            if (this.state.selectedCard && this.state.selectedCard.id === card.id) {
                this.state.selectedCard = false;
            } else {
                this.state.selectedCard = card;
            }
            this.render();
        }
        // Lifecycle hooks
        back() {
            if(this.state.detailIsShown) {
                this.state.detailIsShown = false;
                this.render();
            } else {
                this.trigger('close-screen');
            }
        }
        activateEditMode(event) {
            const { isNewClient } = event.detail;
            this.state.isEditMode = true;
            this.state.detailIsShown = true;
            this.state.isNewClient = isNewClient;
            if (!isNewClient) {
                this.state.editModeProps = {
                    partner: this.state.selectedClient,
                };
            }
            this.render();
        }
        deactivateEditMode() {
            this.state.isEditMode = false;
            this.state.editModeProps = {
                partner: {
                    country_id: this.env.pos.company.country_id,
                    state_id: this.env.pos.company.state_id,
                },
            };
            this.render();
        }
        cancelEdit() {
            this.deactivateEditMode();
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
        async createNewGiftCard(event) {
            const { isNewGiftCard } = event.detail;
            const { confirmed,payload } = await this.showTempScreen('giftCardCreateScreen');
            if (confirmed) {
                if (this.env.pos.config.msg_before_card_pay){
                    var customer = this.env.pos.db.get_partner_by_id(Number(payload["customer_id"]))
                    var card_type = this.env.pos.card_type
                    var card_type_name = ''
                    _.each(card_type, function(result){
                        if(result['id'] == Number(payload["card_type"])){
                            card_type_name = result['name']
                        }
                    });
                    const { confirmed,getConfirmPayload } = await this.showPopup('giftCardCreatePopupConform', {
                        title: this.env._t('Confirm'),
                        CardNumber: payload["card_no"],
                        SelectCustomer: customer.name,
                        ExpireDate :payload["expire_date"],
                        Amount: payload["card_value"],
                        SelectCardType: card_type_name,
                    });
                    if (confirmed) {
                        var product_id = this.env.pos.config.gift_card_product_id[0];
                        var customer_id = Number(payload["customer_id"]);
                        this.env.pos.get_order().set_is_rounding(false);
                        var product = this.env.pos.db.get_product_by_id(product_id);
                        var gift_card = this.env.pos.get_order().set_giftcard(payload);
                        var customer = this.env.pos.db.get_partner_by_id(customer_id);
                        var amount = payload["card_value"];
                        this.orderIsEmpty(this.env.pos.get_order());
                        this.env.pos.get_order().set_client(customer);
                        this.env.pos.get_order().add_product(product, {
                            price: amount,
                            extras: {
                                price_manually_set: true,
                            },
                        });
                        this.render();
                        this.state.showGiftPaymentControlBtn = false;
                        this.showScreen('PaymentScreen',{'showGiftButton': false });
                    }
                }else{
                    this.env.pos.get_order().set_is_rounding(false);
                    var product = this.env.pos.db.get_product_by_id(this.env.pos.config.gift_card_product_id[0]);
                    var customer = this.env.pos.db.get_partner_by_id(Number(payload["customer_id"]));
                    var amount = payload["card_value"];
                    var gift_card = this.env.pos.get_order().set_giftcard(payload);
                    this.orderIsEmpty(this.env.pos.get_order());
                    this.env.pos.get_order().set_client(customer);
                    this.env.pos.get_order().add_product(product, {
                        price: amount,
                        extras: {
                            price_manually_set: true,
                        },
                    });
                    this.render();
                    this.showScreen('PaymentScreen');
                }
            }
        }
        get GiftCardList() {
            return this.env.pos.get('gift_card_order_list');
        }
        _onSearch(event) {
            const searchDetails = event.detail;
            Object.assign(this.searchDetails, searchDetails);
            this.render();
        }
        get filteredGiftCardList() {
            const filterCheck = (order) => {
                if (this.filter && this.filter !== 'All Gift Card') {
                    const screen = this.env.pos.get('gift_card_order_list');
                    return this.filter === this.constants.screenToStatusMap[screen.name];
                }
                return true;
            };
            const { fieldValue, searchTerm } = this.searchDetails;
            const fieldAccessor = this._searchFields[fieldValue];
            const searchCheck = (order) => {
                if (!fieldAccessor) return true;
                const fieldValue = fieldAccessor(order);
                if (fieldValue === null) return true;
                if (!searchTerm) return true;
                return fieldValue && fieldValue.toString().toLowerCase().includes(searchTerm.toLowerCase());
            };
            const predicate = (order) => {
                return filterCheck(order) && searchCheck(order);
            };
            return this.GiftCardList.filter(predicate);
            
        }
        get searchBarConfig() {
            return {
                searchFields: this.constants.searchFieldNames,
                filter: { show: true, options: this.filterOptions },
            };
        }
        get filterOptions() {
            return ['All Card'];
        }
        showCardholderName() {
            return false;
        }
        get _searchFields() {
            var fields = {
                'Card Number': (order) => order.card_no,
                'Issue Date(YYYY-MM-DD hh:mm A)': (order) => moment(order.issue_date).format('YYYY-MM-DD hh:mm A'),
                'Expire Date(YYYY-MM-DD hh:mm A)': (order) => moment(order.expire_date).format('YYYY-MM-DD hh:mm A'),
                Customer: (order) => order.customer_id[1],
            };
            return fields;
        }
        _initializeSearchFieldConstants() {
            this.constants = {};
            Object.assign(this.constants, {
                searchFieldNames: Object.keys(this._searchFields),
            });
        }
    }
    GiftCardScreen.template = 'GiftCardScreen';

    Registries.Component.add(GiftCardScreen);

    return GiftCardScreen;
});
