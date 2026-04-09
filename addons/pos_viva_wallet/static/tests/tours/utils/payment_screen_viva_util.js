/** @odoo-module */

export function simulateKioskNamelessCashier() {
    return [
        {
            content: "Simulate kiosk: cashier has no usable name",
            trigger: ".payment-screen",
            run: function () {
                const pos = window.posmodel;
                pos._vivaWalletTestOrigGetCashier = pos.getCashier.bind(pos);
                pos.getCashier = () => ({
                    name: "",
                    id: 1,
                    _role: "cashier",
                    raw: { role: "cashier" },
                });
            },
        },
    ];
}

export function send_payment_cancel() {
    return [
        {
            content: "click send button",
            trigger: ".button.send_payment_cancel",
            run: "click",
        },
    ];
}
