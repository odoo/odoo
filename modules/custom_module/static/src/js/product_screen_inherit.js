/* @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";


// Fonction pour désactiver les interactions sur les anciennes lignes de commande
const disableInteractionOnOldOrders = (orderLines, isAdmin) => {
    orderLines.forEach(line => {
        if (!isAdmin && line.classList.contains("orderline") && !line.classList.contains("text-success")) {
            line.classList.remove("cursor-pointer");
            line.style.pointerEvents = "none";
            line.style.userSelect = "none";
            line.style.cursor = "not-allowed";

            const numpadButtons = document.querySelectorAll(".numpad button");
            numpadButtons.forEach(button => {
                button.disabled = true;
                button.style.pointerEvents = "none";
            });
        }
    });
};

// Fonction pour supprimer la classe 'selected' des lignes de commande
const removeSelectedClass = () => {
    const selectedOrderLines = document.querySelectorAll(".orderline.selected");
    selectedOrderLines.forEach(el => {
        el.classList.remove("selected");
    });
};

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        try {
            const pos = this.pos;
            const currentUser = pos.cashier;
            const isAdmin = currentUser.role === "admin" || currentUser.role === "manager";
            // Timeout pour donner le temps à l'interface de se charger avant d'appliquer les changements
            setTimeout(() => {
                if (!isAdmin) {
                    const orderLines = document.querySelectorAll(".orderline:not(.text-success)");
                    disableInteractionOnOldOrders(orderLines, isAdmin);
                    removeSelectedClass();
                }
            }, 100);

            // Observer pour surveiller les changements dans l'UI
            const orderContainer = document.querySelector(".order-container");
            if (orderContainer) {
                const observer = new MutationObserver(() => {
                    const orderLines = document.querySelectorAll(".orderline:not(.text-success)");
                    disableInteractionOnOldOrders(orderLines, isAdmin);
                    removeSelectedClass();
                });
                observer.observe(orderContainer, { subtree: true, childList: true });
            }

        } catch (error) {
            console.error("Une erreur s'est produite dans le patch de ProductScreen :", error);
        }
    },


});
