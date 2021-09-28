odoo.define('point_of_sale.ClosePosPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { identifyError } = require('point_of_sale.utils');
    const { ConnectionLostError, ConnectionAbortedError} = require('@web/core/network/rpc_service')

    /**
     * This popup needs to be self-dependent because it needs to be called from different place.
     */
    class ClosePosPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.manualInputCashCount = true;
            this.cashControl = this.env.pos.config.cash_control;
            this.moneyDetailsRef = useRef('moneyDetails');
            this.closeSessionClicked = false;
            this.moneyDetails = null;
            this.state = useState({});
        }
        async willStart() {
            try {
                const closingData = await this.rpc({
                    model: 'pos.session',
                    method: 'get_closing_control_data',
                    args: [[this.env.pos.pos_session.id]]
                });
                this.ordersDetails = closingData.orders_details;
                this.paymentsAmount = closingData.payments_amount;
                this.payLaterAmount = closingData.pay_later_amount;
                this.openingNotes = closingData.opening_notes;
                this.defaultCashDetails = closingData.default_cash_details;
                this.otherPaymentMethods = closingData.other_payment_methods;

                // component state and refs definition
                const state = {notes: '', acceptClosing: false};
                if (this.cashControl) {
                    state[this.defaultCashDetails.name] = {counted: 0, difference: -this.defaultCashDetails.amount};
                }
                if (this.otherPaymentMethods.length > 0) {
                    this.otherPaymentMethods.forEach(pm => {
                        state[pm.name] = {counted: this.env.pos.round_decimals_currency(pm.amount), difference: 0}
                    })
                }
                Object.assign(this.state, state);
            } catch (error) {
                this.error = error;
            }
        }
        /*
         * Since this popup need to be self dependent, in case of an error, the popup need to be closed on its own.
         */
        mounted() {
            if (this.error) {
                this.cancel();
                if (identifyError(this.error) instanceof ConnectionLostError) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Please check your internet connection and try again.'),
                    });
                } else {
                    throw this.error;
                }
            }
        }
        openDetailsPopup() {
            if (this.moneyDetailsRef.comp.isClosed()){
                this.moneyDetailsRef.comp.openPopup();
                this.state[this.defaultCashDetails.name].counted = 0;
                this.state.notes = '';
                if (this.manualInputCashCount) {
                    this.moneyDetailsRef.comp.reset();
                }
            }
        }
        handleInputChange() {
            this.manualInputCashCount = true;
            this.state.notes = '';
            this.state[this.defaultCashDetails.name].difference =
                this.env.pos.round_decimals_currency(this.state[this.defaultCashDetails.name].counted - this.defaultCashDetails.amount);
        }
        updateCountedCash(event) {
            const { total, moneyDetailsNotes, moneyDetails } = event.detail;
            this.state[this.defaultCashDetails.name].counted = total;
            this.state[this.defaultCashDetails.name].difference =
                this.env.pos.round_decimals_currency(this.state[[this.defaultCashDetails.name]].counted - this.defaultCashDetails.amount);
            if (moneyDetailsNotes) {
                this.state.notes = moneyDetailsNotes;
            }
            this.manualInputCashCount = false;
            this.moneyDetails = moneyDetails;
        }
        canCloseSession() {
            return !this.cashControl || !this.state[this.defaultCashDetails.name].difference || this.state.acceptClosing;
        }
        closePos() {
            this.trigger('close-pos');
        }
        async closeSession() {
            if (this.canCloseSession() && !this.closeSessionClicked) {
                this.closeSessionClicked = true;
                let response;
                if (this.cashControl) {
                     response = await this.rpc({
                        model: 'pos.session',
                        method: 'post_closing_cash_details',
                        args: [this.env.pos.pos_session.id],
                        kwargs: {
                            counted_cash: this.state[this.defaultCashDetails.name].counted,
                        }
                    })
                    if (!response.successful) {
                        return this.handleClosingError(response);
                    }
                }
                await this.rpc({
                    model: 'pos.session',
                    method: 'update_closing_control_state_session',
                    args: [this.env.pos.pos_session.id, this.state.notes]
                })
                try {
                    response = await this.rpc({
                        model: 'pos.session',
                        method: 'close_session_from_ui',
                        args: [this.env.pos.pos_session.id],
                    });
                    if (!response.successful) {
                        return this.handleClosingError(response);
                    }
                    window.location = '/web#action=point_of_sale.action_client_pos_menu';
                } catch (error) {
                    const iError = identifyError(error);
                    if (iError instanceof ConnectionLostError || iError instanceof ConnectionAbortedError) {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Network Error'),
                            body: this.env._t('Cannot close the session when offline.'),
                        });
                    } else {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Closing session error'),
                            body: this.env._t(
                                'An error has occurred when trying to close the session.\n' +
                                'You will be redirected to the back-end to manually close the session.')
                        })
                        window.location = '/web#action=point_of_sale.action_client_pos_menu';
                    }
                }
                this.closeSessionClicked = false;
            }
        }
        async handleClosingError(response) {
            await this.showPopup('ErrorPopup', {title: 'Error', body: response.message});
            if (response.redirect) {
                window.location = '/web#action=point_of_sale.action_client_pos_menu';
            }
        }
    }

    ClosePosPopup.template = 'ClosePosPopup';
    Registries.Component.add(ClosePosPopup);

    return ClosePosPopup;
});
