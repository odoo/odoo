import { useEffect, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export const useTrackedFinalizedOrder = (initialOrderUuid, isOrderLocked) => {
    const pos = usePos();
    const state = useState({ trackedOrderUuid: initialOrderUuid });

    const findOrderByUuid = (uuid) => pos.models["pos.order"].getBy("uuid", uuid);

    useEffect(
        () => {
            const trackedOrder = findOrderByUuid(state.trackedOrderUuid);
            if (!trackedOrder || !trackedOrder.finalized || !isOrderLocked()) {
                return;
            }

            pos.showScreen(pos.firstScreen);
            pos.notification.add(
                _t(
                    "Order has been %s from another device.",
                    trackedOrder.state === "cancel" ? _t("Cancelled") : _t("Paid")
                ),
                { type: "warning" }
            );
        },
        () => [state.trackedOrderUuid, findOrderByUuid(state.trackedOrderUuid)?.state]
    );
};
