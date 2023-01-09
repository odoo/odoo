odoo.define('fg_custom.FgTicketScreen', function (require) {
    'use strict';

    const TicketScreen = require('point_of_sale.TicketScreen');
    const Registries = require('point_of_sale.Registries');

    const FgTicketScreen = (TicketScreen) =>
        class extends TicketScreen {
            _getSearchFields() {
                const fields = {
                SI_NUMBER: {
                    repr: (order) => order.name,
                    displayName: this.env._t('SI Reference Number'),
                    modelField: 'pos_si_trans_reference',
                },
                REFUND_NUMBER: {
                    repr: (order) => order.name,
                    displayName: this.env._t('Refund Reference Number'),
                    modelField: 'pos_refund_si_reference',
                },
                DATE: {
                    repr: (order) => moment(order.creation_date).format('YYYY-MM-DD hh:mm A'),
                    displayName: this.env._t('Date'),
                    modelField: 'date_order',
                },
                CUSTOMER: {
                    repr: (order) => order.get_client_name(),
                    displayName: this.env._t('Customer'),
                    modelField: 'partner_id.display_name',
                }
                }
                return fields;
            }
        };

    Registries.Component.extend(TicketScreen, FgTicketScreen);

    return TicketScreen;
});