odoo.define('pos_restaurant.tour.BillScreenTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        clickOk() {
            return [
                {
                    content: `go back`,
                    trigger: `.receipt-screen .button.next`,
                },
            ];
        }
        clickBillButton() {
            return [
                {
                    content: "click bill button",
                    trigger: '.control-button:contains("Bill")',
                },
            ];
        }
    }

    class Check {
        isShown() {
            return [
                {
                    content: 'Bill screen is shown',
                    trigger: '.receipt-screen h1:contains("Bill Printing")',
                    run: () => {},
                },
            ];
        }
        isQRCodeShown() {
            return [
                {
                    content: "QR codes are shown",
                    trigger: '#posqrcode',
                    run: () => {},
                },
            ];
        }
        isQRCodeNotShown() {
            return [
                {
                    content: "QR codes are shown",
                    trigger: 'body:not(:has(#posqrcode))',
                    run: () => {},
                },
            ];
        }
    }

    return createTourMethods('BillScreen', Do, Check);
});
