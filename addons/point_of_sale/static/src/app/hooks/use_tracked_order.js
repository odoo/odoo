import { useEffect } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "../store/pos_hook";

export const ALLOWED_SCREENS = ["ReceiptScreen", "TipScreen"];

export const useTrackedOrder = (orderUuid) => {
    const pos = usePos();
    const order = pos.models["pos.order"].getBy("uuid", orderUuid);
    const resetScreen = () => {
        if (pos.firstScreen === pos.mainScreen.component.name) {
            pos.add_new_order();
        }

        pos.showScreen(pos.firstScreen);
        pos.notification.add(_t("Order has been finalized from another devices."), {
            type: "warning",
        });
    };

    useEffect(
        (state) => {
            // Loading do nothing
            if (pos.env.services.ui.isBlocked) {
                return;
            }

            const currentScreen = pos.mainScreen.component.name;
            const orderFinalized = state === "paid" || state === "invoiced";
            const screenIsAllowed = ALLOWED_SCREENS.includes(currentScreen);

            if (!odoo.debug === "assets") {
                console.debug(orderUuid, orderFinalized, screenIsAllowed);
            }

            // Everything is normal, do nothing
            if (state === "draft") {
                return;
            }

            // If the current screen is compatible with finalized orders, do nothing.
            if (screenIsAllowed && orderFinalized) {
                return;
            }

            // If the order is cancelled or finalized on a wrong screen, redirect the user
            if (state === "cancel" || (!screenIsAllowed && orderFinalized)) {
                return resetScreen();
            }
        },
        () => [order.state]
    );
};
