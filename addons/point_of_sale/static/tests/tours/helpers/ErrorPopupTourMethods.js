odoo.define('point_of_sale.tour.ErrorPopupTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        clickConfirm() {
            return [
                {
                    content: 'click confirm button',
                    trigger: '.popup-error .footer .cancel',
                },
            ];
        }
    }

    class Check {
        isShown() {
            return [
                {
                    content: 'error popup is shown',
                    trigger: '.modal-dialog .popup-error',
                    run: () => {},
                },
            ];
        }

        messageBodyContains(text) {
            return [
                {
                    content: `check '${text}' is in the body of the popup`,
                    trigger: `.modal-dialog .popup-error .body:contains(${text})`,
                }
            ];
        }
    }

    return createTourMethods('ErrorPopup', Do, Check);
});
