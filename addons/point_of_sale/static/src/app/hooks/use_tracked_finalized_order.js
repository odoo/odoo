import { useEffect } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "../store/pos_hook";

export const useTrackedFinalizedOrder = (
    orderUuid,
    targetScreen = null,
    recreateOrder = false,
    isLocked = () => false
) => {
    const pos = usePos();
    const order = pos.models["pos.order"].getBy("uuid", orderUuid);

    useEffect(
        (state) => {
            if (state !== "draft" && recreateOrder) {
                pos.add_new_order();
            }

            if (state !== "draft" && !isLocked()) {
                pos.showScreen(targetScreen || pos.firstScreen);
                pos.notification.add(_t("Order has been cancelled from another devices."), {
                    type: "warning",
                });
            }
        },
        () => [order.state]
    );
};
