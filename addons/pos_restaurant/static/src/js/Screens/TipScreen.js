odoo.define('pos_restaurant.TipScreen', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const PosComponent = require('point_of_sale.PosComponent');
    const { parse } = require('web.field_utils');
    const { useState } = owl.hooks;

    class TipScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({ inputCustomAmount: '' });
            this._totalAmount = this.currentOrder.get_total_with_tax();
        }
        get totalAmount() {
            return this._totalAmount;
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        get percentageTips() {
            return [
                { percentage: '15%', amount: 0.15 * this.totalAmount },
                { percentage: '20%', amount: 0.2 * this.totalAmount },
                { percentage: '25%', amount: 0.25 * this.totalAmount },
            ];
        }
        async setTip(amount) {
            const order = this.env.pos.get_order();
            const serverId = this.env.pos.validated_orders_name_server_id_map[order.name];

            if (!serverId) {
                this.showPopup('ErrorPopup', {
                    title: 'Unsynced order',
                    body: 'This order is not yet synced to server. Make sure it is synced then try again.',
                });
                return;
            }

            // set the tip by temporarily allowing order modification
            order.finalized = false;
            order.set_tip(amount);
            order.finalized = true;

            // set_tip calls add_product which sets the new line as the selected_orderline
            const tip_line = order.selected_orderline;
            await this.rpc({
                method: 'set_tip',
                model: 'pos.order',
                args: [serverId, tip_line.export_as_JSON()],
            });
            this.goNextScreen();
        }
        async tipCustomAmount() {
            const tipAmount = parse.float(this.state.inputCustomAmount);
            if (tipAmount > 0.25 * this._totalAmount) {
                const { confirmed } = await this.showPopup('ConfirmPopup', {
                    title: 'Are you sure?',
                    body: `${this.env.pos.format_currency(
                        tipAmount
                    )} is more than 25% of the order's total amount. Are you sure of this tip amount?`,
                });
                if (!confirmed) return;
            }
            await this.setTip(tipAmount);
        }
        goNextScreen() {
            this.env.pos.get_order().finalize();
            const { name, props } = this.nextScreen;
            this.showScreen(name, props);
        }
        get nextScreen() {
            if (this.env.pos.config.module_pos_restaurant && this.env.pos.config.iface_floorplan) {
                const table = this.env.pos.table;
                return { name: 'FloorScreen', props: { floor: table ? table.floor : null } };
            } else {
                return { name: 'ProductScreen' };
            }
        }
    }
    TipScreen.template = 'pos_restaurant.TipScreen';

    Registries.Component.add(TipScreen);

    return TipScreen;
});
