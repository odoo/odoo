/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";


const disableInteractionOnOldOrders = (orderLines, isAdmin) => {
    orderLines.forEach(line => {
        if (!isAdmin && line.classList.contains("orderline") && !line.classList.contains("text-success")) {
            line.classList.remove("cursor-pointer");
            line.style.pointerEvents = "none";
            line.style.userSelect = "none";
            line.style.cursor = "not-allowed";
        }
    });
};

const removeSelectedClass = () => {
    const selectedOrderLines = document.querySelectorAll(".orderline.selected");
    selectedOrderLines.forEach(el => {
        el.classList.remove("selected");
    });
};
function checkForChanges() {
    let hasOtherChanges = false;
    const orderLines = document.querySelectorAll('.order-container .orderline');
    for (const line of orderLines) {
        if (line.classList.contains('has-change')) {
            hasOtherChanges = true;
            break;
        }
    }
    return hasOtherChanges;
}
patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);
        try {
            const pos = this.pos;
            const currentUser = pos.cashier;
            const isAdmin = currentUser._role === "admin" || currentUser._role === "manager";
            setTimeout(() => {
                if (!isAdmin) {
                    if(!checkForChanges()){
                        const numpadButtons = document.querySelectorAll(".numpad button");
                        numpadButtons.forEach(button => {
                            button.disabled = true;
                            button.style.pointerEvents = "none";
                            console.log(' after ActionpadWidget call')
                        });
                    }
                    const oldOrderLines = document.querySelectorAll(".orderline:not(.text-success)");
                    disableInteractionOnOldOrders(oldOrderLines, isAdmin);

                    removeSelectedClass();
                }
            }, 100);

            // Observer pour surveiller les changements dans l'UI
            const orderContainer = document.querySelector(".order-container");
            if (orderContainer) {
                const observer = new MutationObserver(() => {
                    const orderLines = document.querySelectorAll(".orderline:not(.text-success)");
                    disableInteractionOnOldOrders(orderLines, isAdmin);
                    if(!checkForChanges()){
                        const numpadButtons = document.querySelectorAll(".numpad button");
                        numpadButtons.forEach(button => {
                            button.style.pointerEvents = "none";
                            button.disabled = true;
                        });
                    }
                    removeSelectedClass();
                });
                observer.observe(orderContainer, { subtree: true, childList: true });
            }

        } catch (error) {
            console.error("Une erreur s'est produite dans le patch de ProductScreen :", error);
        }
    },


    async submitOrder() {
        const res = await super.submitOrder();
        this.pos.showScreen("FloorScreen");
        return res
    },
});
