odoo.define('point_of_sale.tour.ChromeTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        newOrder() {
            return [
                {
                    content: 'new order',
                    trigger: '.order-selector .neworder-button',
                },
            ];
        }
        deleteOrder() {
            return [
                {
                    content: 'delete current order',
                    trigger: '.order-selector .deleteorder-button',
                },
            ];
        }
        selectOrder(orderSequence) {
            return [
                {
                    content: `select order '${orderSequence}'`,
                    trigger: `.order-selector .order-sequence:contains("${orderSequence}")`,
                },
            ];
        }
        confirmPopup() {
            return [
                {
                    content: 'confirm popup',
                    trigger: '.popups .modal-dialog .button.confirm',
                },
            ];
        }
    }

    return { Do, Chrome: createTourMethods('Chrome', Do) };
});
