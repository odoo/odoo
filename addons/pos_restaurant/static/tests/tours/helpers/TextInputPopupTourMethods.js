odoo.define('pos_restaurant.tour.TextInputPopupTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        inputText(val) {
            return [
                {
                    content: `input text '${val}'`,
                    trigger: `.modal-dialog .popup-textinput input`,
                    run: `text ${val}`,
                },
            ];
        }
        clickConfirm() {
            return [
                {
                    content: 'confirm text input popup',
                    trigger: '.modal-dialog .confirm',
                },
            ];
        }
    }

    class Check {
        isShown() {
            return [
                {
                    content: 'text input popup is shown',
                    trigger: '.modal-dialog .popup-textinput',
                    run: () => {},
                },
            ];
        }
    }

    return createTourMethods('TextInputPopup', Do, Check);
});
