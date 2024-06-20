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
        isShown(isShown=true) {
            return [
                {
                    content: 'error popup is ' + (isShown ? '' : 'not ') + 'shown',
                    trigger: isShown ? '.modal-dialog .popup-error' : 'body:not(:has(.modal-dialog .popup-error))',
                    run: () => {},
                },
            ];
        }
    }

    return createTourMethods('ErrorPopup', Do, Check);
});
