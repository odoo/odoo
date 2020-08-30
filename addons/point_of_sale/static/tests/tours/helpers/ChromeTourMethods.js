odoo.define('point_of_sale.tour.ChromeTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        confirmPopup() {
            return [
                {
                    content: 'confirm popup',
                    trigger: '.popups .modal-dialog .button.confirm',
                },
            ];
        }
        clickOrderManagementButton() {
            return [
                {
                    content: 'check order management button is shown',
                    trigger: '.pos .pos-rightheader .order-management',
                    run: () => {},
                },
                {
                    content: 'click order management button',
                    trigger: '.pos .pos-rightheader .order-management',
                },
            ];
        }
        clickTicketButton() {
            return [
                {
                    trigger: '.pos-topheader .ticket-button',
                },
                {
                    trigger: '.subwindow .ticket-screen',
                    run: () => {},
                },
            ];
        }
    }

    return createTourMethods('Chrome', Do);
});
