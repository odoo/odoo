odoo.define('l10n_fr_pos_cert.PaymentScreen', function(require) {

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const session = require('web.session');

    const PosFrPaymentScreen = PaymentScreen => class extends PaymentScreen {
        async _postPushOrderResolve(order, order_server_ids) {
            try {
                if(this.env.pos.is_french_country()) {
                    let result = await this.rpc({
                        model: 'pos.order',
                        method: 'search_read',
                        domain: [['id', 'in', order_server_ids]],
                        fields: ['l10n_fr_hash'],
                        context: session.user_context,
                    });
                    order.set_l10n_fr_hash(result[0].l10n_fr_hash || false);
                }
            } finally {
                return super._postPushOrderResolve(...arguments);
            }
        }
    };

    Registries.Component.extend(PaymentScreen, PosFrPaymentScreen);

    return PaymentScreen;
});
