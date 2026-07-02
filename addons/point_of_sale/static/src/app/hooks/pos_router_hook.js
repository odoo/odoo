import { registry } from "@web/core/registry";
import { usePos, usePosRouter } from "./pos_hook";

/**
 * @param {string} pageName
 */
export function useRouterParamsChecker(pageName) {
    const router = usePosRouter();
    const pos = usePos();
    const routeParams = registry.category("pos_pages").get(pageName);
    const params = routeParams.params;

    if (params.orderUuid && Object.keys(params).includes("orderFinalized")) {
        const order = pos.models["pos.order"].getBy("uuid", router.state.params.orderUuid);
        if (!order || order.finalized !== params.orderFinalized) {
            const defaultPage = pos.defaultPage;
            pos.navigate(defaultPage.page, defaultPage.params);
        }
    }
}
