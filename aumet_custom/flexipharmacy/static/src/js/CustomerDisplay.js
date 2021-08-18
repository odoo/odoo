odoo.define('flexipharmacy.CustomerDisplay', function (require) {
"use strict";

    require('web.Bus');
    var session = require('web.session');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var bus = require('bus.Longpolling');
    var cross_tab = require('bus.CrossTab').prototype;
    var session = require('web.session');

    const PopupControllerMixin = require('point_of_sale.PopupControllerMixin');
    const { Component, hooks } = owl;
    const { useState, useRef } = owl.hooks;
    const { loadCSS } = require('web.ajax');
    const { useListener } = require('web.custom_hooks');
    const { CrashManager } = require('web.CrashManager');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const models = require('flexipharmacy.models');



    class CustomerDisplay extends PopupControllerMixin(PosComponent) {
        constructor() {
            super(...arguments);
            useListener('click-toggle-slider', this._toggleSlider);
            useListener('click-feedback', this._feedbackPopup);
            useListener('click-create-customer', this._customerCreatePopup);
            this.state = useState({ready: false, rightWidth: 0,
                                    cartData: '',
                                    imageSlider: true,
                                    orderAmount: 0,
                                    changeAmount:0,
                                    })
            this.rightPane = useRef('rightpane')
        }
        mounted() {
            $(document).off();
            $(window).off();
            $('html').off();
            $('body').off();
            this.state.rightWidth = this.rightPane.el.clientWidth - 20;
        }
        async start(){
            try {
                const posModelDefaultAttributes = {
                    env: this.env,
                    rpc: this.rpc.bind(this),
                    session: this.env.session,
                };
                this.env.pos = new models.CustomerModel(posModelDefaultAttributes);
                await this.env.pos.ready;
                this._buildChrome();
                this.state.ready = true;
                this._pollData();
            } catch (error) {
                let title = 'Unknown Error',
                    body;

                if (error.message && [100, 200, 404, -32098].includes(error.message.code)) {
                    // this is the signature of rpc error
                    if (error.message.code === -32098) {
                        title = 'Network Failure (XmlHttpRequestError)';
                        body =
                            'The Point of Sale could not be loaded due to a network problem.\n' +
                            'Please check your internet connection.';
                    } else if (error.message.code === 200) {
                        title = error.message.data.message || this.env._t('Server Error');
                        body =
                            error.message.data.debug ||
                            this.env._t(
                                'The server encountered an error while receiving your order.'
                            );
                    }
                } else if (error instanceof Error) {
                    title = error.message;
                    body = error.stack;
                }
                await this.showPopup('ErrorTracebackPopup', {
                    title,
                    body,
                    exitButtonIsShown: true,
                });
            }
        }
        _pollData(){
            this.env.services['bus_service'].updateOption('customer.display',session.uid);
            this.env.services['bus_service'].onNotification(this,this._onNotification);
            this.env.services['bus_service'].startPolling();
            cross_tab._isRegistered = true;
            cross_tab._isMasterTab = true;
        }
        _onNotification(notifications){
            var self = this;
            for (var notif of notifications) {
                if(notif[1].customer_display_data){
                    this.state.cartData = notif[1].customer_display_data;
                }
            }
        }
        _buildChrome() {
            if ($.browser.chrome) {
                var chrome_version = $.browser.version.split('.')[0];
                if (parseInt(chrome_version, 10) >= 50) {
                    loadCSS('/flexipharmacy/static/src/css/chrome51.css');
                }
            }
            this._disableBackspaceBack();
            this._replaceCrashmanager();
        }
        _disableBackspaceBack() {
            $(document).on('keydown', function (e) {
                if (e.which === 8 && !$(e.target).is('input, textarea')) {
                    e.preventDefault();
                }
            });
        }
        _replaceCrashmanager() {
            var self = this;
            CrashManager.include({
                show_error: function (error) {
                    if (self.env.pos) {
                        // self == this component
                        self.showPopup('ErrorTracebackPopup', {
                            title: error.type,
                            body: error.message + '\n' + error.data.debug + '\n',
                        });
                    } else {
                        // this == CrashManager instance
                        this._super(error);
                    }
                },
            });
        }
        _toggleSlider(){
            this.state.imageSlider = !this.state.imageSlider;
        }
        async _feedbackPopup(){
            const { confirmed, payload } = await this.showPopup('CustomerFeedbackPopup');
            if (confirmed) {
                await this.rpc({
                    model: 'customer.display',
                    method: 'send_rating',
                    args: [odoo.config_id, payload],
                });
            }
        }
        async _customerCreatePopup(){
            const { confirmed, payload } = await this.showPopup('CustomerCreatePopup');
            if (confirmed) {
                await this.rpc({
                    model: 'customer.display',
                    method: 'create_customer',
                    args: [payload, odoo.config_id],
                });
            }
        }

    }
    CustomerDisplay.template = 'CustomerDisplay';

    Registries.Component.add(CustomerDisplay);

    return CustomerDisplay;

});