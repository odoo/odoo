import { registry } from "@web/core/registry";
import { usePos } from "./pos_hook";
import { PosRouterPlugin } from "../plugins/pos_router_plugin";
import { usePlugin } from "@odoo/owl";

/**
 * @param {string} pageName
 */
export function useRouterParamsChecker(pageName) {
    const router = usePlugin(PosRouterPlugin);
    const pos = usePos();
    const routeParams = registry.category("pos_pages").get(pageName);
    const params = routeParams.params;

    if (params.orderUuid && Object.keys(params).includes("orderFinalized")) {
        const order = pos.models["pos.order"].getBy("uuid", router.currentScreenParams().orderUuid);
        if (!order || order.finalized !== params.orderFinalized) {
            const defaultPage = pos.defaultPage;
            pos.navigate(defaultPage.page, defaultPage.params);
        }
    }
}
