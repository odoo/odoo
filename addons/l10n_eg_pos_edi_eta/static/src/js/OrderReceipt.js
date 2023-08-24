odoo.define('l10n_eg_pos_edi_eta.OrderReceipt', function (require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const Registries = require('point_of_sale.Registries');

    const {useState} = owl;

    const PosETAOrderReceipt = OrderReceipt =>
        class extends OrderReceipt {
            /**
             * @override
             */
            constructor() {
                super(...arguments);
                this.eta_data = useState({
                    'qr_code': ''
                });
            }

            /**
             * @override
             */
            mounted() {
                this.env.pos.on('order_synchronized', this.loadETAData, this);
                this.env.pos.on('receipt_submitted', this.loadETAData, this);
            }

            get order() {
                return this.receiptEnv.order;
            }

            async willStart() {
                await super.willStart();
                await this.loadETAData()
            }

            async loadETAData() {
                const countryCode = this.order.pos.company.country.code;
                if (countryCode === 'EG' && !this.order.to_invoice) {
                    const orderId = this.env.pos.validated_orders_name_server_id_map[this.order.get_name()]
                    if (orderId) {
                        let eta_result = await this.rpc({
                            model: 'pos.order',
                            method: 'search_read',
                            domain: [['id', '=', orderId]],
                            fields: ['l10n_eg_pos_qrcode']
                        });
                        this.eta_data.qr_code = eta_result[0]['l10n_eg_pos_qrcode'];
                    }
                }
            }
        };

    Registries.Component.extend(OrderReceipt, PosETAOrderReceipt);

    return OrderReceipt;
});
