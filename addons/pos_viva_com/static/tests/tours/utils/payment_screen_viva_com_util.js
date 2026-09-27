/** @odoo-module */

export function simulateKioskNamelessCashier() {
    return [
        {
            content: "Simulate kiosk: cashier has no usable name",
            trigger: ".payment-screen",
            run: function () {
                const pos = window.posmodel;
                pos._vivaComTestOrigGetCashier = pos.accessRight.loggedCashier;
                pos.accessRight.cashier = () => ({
                    name: "",
                    id: 1,
                    _role: "cashier",
                    raw: { role: "cashier" },
                });
            },
        },
    ];
}
