odoo.define('l10n_eg_pos_edi_eta.ReceiptScreen', function (require) {
    'use strict';

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');

    const {useState} = owl;

    const PosETAReceiptScreen = ReceiptScreen =>
        class extends ReceiptScreen {
            /**
             * @override
             */
            constructor() {
                super(...arguments);
                this.eta_result = useState({
                    'state': 'ignore',
                    'error': {},
                    'loading': false
                });
            }

            /**
             * @override
             */
            mounted() {
                this.env.pos.on('order_synchronized', this.checkETAStatus, this);
            }

            /**
             * @override
             */
            async willStart() {
                await super.willStart();
                await this.checkETAStatus()
            }

            async checkETAStatus() {
                const order = this.currentOrder
                const countryCode = order.pos.company.country.code;
                if (countryCode === 'EG' && !order.to_invoice && this.eta_result.state !== 'sent') {
                    const orderId = this.env.pos.validated_orders_name_server_id_map[order.get_name()]
                    try {
                        if (orderId) {
                            let eta_result = await this.rpc({
                                model: 'pos.order',
                                method: 'search_read',
                                domain: [['id', '=', orderId]],
                                fields: ['l10n_eg_pos_eta_state', 'l10n_eg_pos_eta_error']
                            });
                            return this._postProcessETAResults(eta_result[0])
                        }
                    } catch(e) {
                        this.eta_result.error = {'message': this.env._t("Uncaught Exception: ") + e.message}
                    }
                    this.eta_result.state = 'pending'
                }
            }

            async submitToETA() {
                if (this.eta_result.loading || this.eta_result.state !== 'pending') return
                this.eta_result.loading = true;
                this.eta_result.error = {};
                const orderId = this.env.pos.validated_orders_name_server_id_map[this.currentOrder.get_name()]
                try {
                    if (orderId) {
                        let eta_results = await this.rpc({
                            model: 'pos.order',
                            method: 'l10n_eg_pos_eta_process_receipts_from_ui',
                            args: [orderId]
                        });
                        if (eta_results.error) {
                            this.eta_result.error = {'message': eta_results.error}
                        } else {
                            this._postProcessETAResults(eta_results[orderId]);
                            this.env.pos.trigger('receipt_submitted', this.env.pos, this.currentOrder);
                        }
                    } else {
                        await this.env.pos.push_orders(this.currentOrder, {show_error: true});
                    }
                } catch (e) {
                    this.eta_result.error = {'message': this.env._t("Uncaught Exception: ") + e.message}
                }
                this.eta_result.loading = false;
            }

            _postProcessETAResults(results) {
                this.eta_result.state = results.l10n_eg_pos_eta_state
                try {
                    this.eta_result.error = JSON.parse(results.l10n_eg_pos_eta_error)
                } catch (e) {
                    this.eta_result.error = {
                        'message': results.l10n_eg_pos_eta_error || this.env._t('Unknown Error: Could not parse error message')
                    }
                }
            }

            get showError() {
                return !_.isEmpty(this.eta_result.error) && this.eta_result.state !== 'sent'
            }
        };

    Registries.Component.extend(ReceiptScreen, PosETAReceiptScreen);

    return ReceiptScreen;
});
