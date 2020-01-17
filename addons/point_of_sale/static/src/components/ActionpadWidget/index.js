odoo.define('point_of_sale.ActionpadWidget', function(require) {
    'use strict';

    const { Component } = owl;

    class ActionpadWidget extends Component {
        constructor() {
            super(...arguments);
            this.pos = this.props.pos;
            this.gui = this.props.gui;
        }
        mounted() {
            this.pos.on('change:selectedClient', () => {
                this.render();
            });
        }
        willUnmount() {
            this.pos.off('change:selectedClient');
        }
        get isLongName() {
            return this.pos.get_client() && this.pos.get_client().name.length > 10;
        }
        get client() {
            return this.pos.get_client();
        }
        startPayment() {
            const productLotsAreValid = this.pos
                .get_order()
                .get_orderlines()
                .every(line => line.has_valid_product_lot());

            if (!productLotsAreValid) {
                this.gui.show_popup('confirm', {
                    title: _t('Empty Serial/Lot Number'),
                    body: _t('One or more product(s) required serial/lot number.'),
                    confirm: function() {
                        this.gui.show_screen('payment');
                    },
                });
            } else {
                this.gui.show_screen('payment');
            }
        }
        selectCustomer() {
            this.gui.show_screen('clientlist');
        }
    }

    return { ActionpadWidget };
});
