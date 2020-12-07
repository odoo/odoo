odoo.define('l10n_fr_pos_cert.PointOfSaleModel', function (require) {
    'use strict';

    const PointOfSaleModel = require('point_of_sale.PointOfSaleModel');
    const session = require('web.session');
    const { patch } = require('web.utils');
    const core = require('web.core');
    const _t = core._t;

    patch(PointOfSaleModel.prototype, 'l10n_fr_pos_cert', {
        async _postPushOrder(order) {
            await this._super(...arguments);
            if (this.isFrenchCountry()) {
                const result = await this._rpc({
                    model: 'pos.order',
                    method: 'search_read',
                    domain: [['id', '=', order._extras.server_id]],
                    fields: ['l10n_fr_hash'],
                    context: session.user_context,
                });
                order.l10n_fr_hash = result[0].l10n_fr_hash || false;
            }
        },
        isFrenchCountry() {
            const french_countries = ['FR', 'MF', 'MQ', 'NC', 'PF', 'RE', 'GF', 'GP', 'TF'];
            if (!this.country) {
                this.ui.askUser('ErrorPopup', {
                    title: _t('Missing Country'),
                    body: _.str.sprintf(_t("The company %s doesn't have a country set."), this.company.name),
                });
                return false;
            }
            return _.contains(french_countries, this.country.code);
        },
        _cannotRemoveOrderLine() {
            return this.isFrenchCountry() ? true : this._super(...arguments);
        },
        getOrderInfo(order) {
            const result = this._super(...arguments);
            result.l10n_fr_hash = order.l10n_fr_hash;
            return result;
        },
        shouldDisallowDecreaseQuantity() {
            return this.isFrenchCountry() || this._super();
        },
        shouldDisallowOrderlineDeletion() {
            return this.isFrenchCountry() || this._super();
        },
    });

    return PointOfSaleModel;
});
