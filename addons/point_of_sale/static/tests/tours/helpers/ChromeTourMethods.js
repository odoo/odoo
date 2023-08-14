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

    class Check {
        isCashMoveButtonHidden() {
            return [
                {
                    trigger: '.pos-topheader:not(:contains(Cash In/Out))',
                    run: () => {},
                }
            ];
        }

        isCashMoveButtonShown() {
            return [
                {
                    trigger: '.pos-topheader:contains(Cash In/Out)',
                    run: () => {},
                }
            ];
        }
    }

    return createTourMethods('Chrome', Do, Check);
});
