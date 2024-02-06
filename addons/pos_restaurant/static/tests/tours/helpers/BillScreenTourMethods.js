/** @odoo-module */

<<<<<<< HEAD
export function clickOk() {
    return [
        {
            content: `go back`,
            trigger: `.receipt-screen .button.next`,
        },
    ];
||||||| parent of ab403dd0c93c (temp)
import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";

class Do {
    clickOk() {
        return [
            {
                content: `go back`,
                trigger: `.receipt-screen .button.next`,
            },
        ];
    }
=======
import { createTourMethods } from "@point_of_sale/../tests/tours/helpers/utils";

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
>>>>>>> ab403dd0c93c (temp)
}

<<<<<<< HEAD
export function isShown() {
    return [
        {
            content: "Bill screen is shown",
            trigger: '.receipt-screen h2:contains("Bill Printing")',
            run: () => {},
        },
    ];
||||||| parent of ab403dd0c93c (temp)
class Check {
    isShown() {
        return [
            {
                content: "Bill screen is shown",
                trigger: '.receipt-screen h1:contains("Bill Printing")',
                run: () => {},
            },
        ];
    }
=======
class Check {
    isShown() {
        return [
            {
                content: "Bill screen is shown",
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
>>>>>>> ab403dd0c93c (temp)
}

export function clickBillButton() {
    return [
        {
            content: "click review button",
            trigger: ".btn-switchpane.review-button",
            mobile: true,
        },
        {
            content: "click more button",
            trigger: ".mobile-more-button",
            mobile: true,
        },
        {
            content: "click bill button",
            trigger: '.control-button:contains("Bill")',
        },
    ];
}

export function isQRCodeShown() {
    return [
        {
            content: "QR codes are shown",
            trigger: '#posqrcode',
            run: () => {},
        },
    ];
}
