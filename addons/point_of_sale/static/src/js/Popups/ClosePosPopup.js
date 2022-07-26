odoo.define('point_of_sale.ClosePosPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { identifyError } = require('point_of_sale.utils');
    const { ConnectionLostError, ConnectionAbortedError} = require('@web/core/network/rpc_service')

    const { onWillStart, useState } = owl;

    /**
     * This popup needs to be self-dependent because it needs to be called from different place.
     */
    class ClosePosPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.manualInputCashCount = false;
            this.cashControl = this.env.pos.config.cash_control;
            this.closeSessionClicked = false;
            this.moneyDetails = null;
            this.state = useState({
                displayMoneyDetailsPopup: false,
            });
            onWillStart(this.onWillStart);
        }
        async onWillStart() {
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
                this.isManager = closingData.is_manager;
                this.amountAuthorizedDiff = closingData.amount_authorized_diff;

                // component state and refs definition
                const state = {notes: '', payments: {}};
                if (this.cashControl) {
                    state.payments[this.defaultCashDetails.id] = {counted: 0, difference: -this.defaultCashDetails.amount, number: 0};
                }
                if (this.otherPaymentMethods.length > 0) {
                    this.otherPaymentMethods.forEach(pm => {
                        if (pm.type === 'bank') {
                            state.payments[pm.id] = {counted: this.env.pos.round_decimals_currency(pm.amount), difference: 0, number: pm.number}
                        }
                    })
                }
                Object.assign(this.state, state);
            } catch (error) {
                super.cancel();
                if (identifyError(error) instanceof ConnectionLostError) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Please check your internet connection and try again.'),
                    });
                } else {
                    throw error;
                }
            }
        }
        //@override
        async confirm() {
            if (!this.cashControl || !this.hasDifference()) {
                this.closeSession();
            } else if (this.hasUserAuthority()) {
                const { confirmed } = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Payments Difference'),
                    body: this.env._t('Do you want to accept payments difference and post a profit/loss journal entry?'),
                });
                if (confirmed) {
                    this.closeSession();
                }
            } else {
                await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Payments Difference'),
                    body: _.str.sprintf(
                        this.env._t('The maximum difference allowed is %s.\n\
                        Please contact your manager to accept the closing difference.'),
                        this.env.pos.format_currency(this.amountAuthorizedDiff)
                    ),
                    confirmText: this.env._t('OK'),
                })
            }
        }
        //@override
        async cancel() {
            if (this.canCancel()) {
                super.cancel();
            }
        }
        openDetailsPopup() {
            this.state.payments[this.defaultCashDetails.id].counted = 0;
            this.state.payments[this.defaultCashDetails.id].difference = -this.defaultCashDetails.amount;
            this.state.notes = "";
            this.state.displayMoneyDetailsPopup = true;
        }
        closeDetailsPopup() {
            this.state.displayMoneyDetailsPopup = false;
        }
        async downloadSalesReport() {
            await this.env.legacyActionManager.do_action('point_of_sale.sale_details_report', {
                additional_context: {
                    active_ids: [this.env.pos.pos_session.id],
                },
            });
        }
        handleInputChange(paymentId) {
            let expectedAmount;
            if (paymentId === this.defaultCashDetails.id) {
                this.manualInputCashCount = true;
                this.state.notes = '';
                expectedAmount = this.defaultCashDetails.amount;
            } else {
                expectedAmount = this.otherPaymentMethods.find(pm => paymentId === pm.id).amount;
            }
            this.state.payments[paymentId].difference =
                this.env.pos.round_decimals_currency(this.state.payments[paymentId].counted - expectedAmount);
        }
        updateCountedCash({ total, moneyDetailsNotes, moneyDetails }) {
            this.state.payments[this.defaultCashDetails.id].counted = total;
            this.state.payments[this.defaultCashDetails.id].difference =
                this.env.pos.round_decimals_currency(this.state.payments[[this.defaultCashDetails.id]].counted - this.defaultCashDetails.amount);
            if (moneyDetailsNotes) {
                this.state.notes = moneyDetailsNotes;
            }
            this.manualInputCashCount = false;
            this.moneyDetails = moneyDetails;
            this.closeDetailsPopup();
        }
        hasDifference() {
            return Object.entries(this.state.payments).find(pm => pm[1].difference != 0);
        }
        hasUserAuthority() {
            const absDifferences = Object.entries(this.state.payments).map(pm => Math.abs(pm[1].difference));
            return this.isManager || this.amountAuthorizedDiff == null || Math.max(...absDifferences) <= this.amountAuthorizedDiff;
        }
        canCancel() {
            return true;
        }
        closePos() {
            this.trigger('close-pos');
        }
        async closeSession() {
            if (!this.closeSessionClicked) {
                this.closeSessionClicked = true;
                let response;
                if (this.cashControl) {
                     response = await this.rpc({
                        model: 'pos.session',
                        method: 'post_closing_cash_details',
                        args: [this.env.pos.pos_session.id],
                        kwargs: {
                            counted_cash: this.state.payments[this.defaultCashDetails.id].counted,
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
                    const bankPaymentMethodDiffPairs = this.otherPaymentMethods
                        .filter((pm) => pm.type == 'bank')
                        .map((pm) => [pm.id, this.state.payments[pm.id].difference]);
                    response = await this.rpc({
                        model: 'pos.session',
                        method: 'close_session_from_ui',
                        args: [this.env.pos.pos_session.id, bankPaymentMethodDiffPairs],
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
        _getShowDiff(pm) {
            return pm.type == 'bank' && pm.number !== 0;
        }
    }

    ClosePosPopup.template = 'ClosePosPopup';
    Registries.Component.add(ClosePosPopup);

    return ClosePosPopup;
});
