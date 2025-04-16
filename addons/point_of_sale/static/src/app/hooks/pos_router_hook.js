import { registry } from "@web/core/registry";
import { usePos, usePosRouter } from "./pos_hook";
import { useComponent } from "@odoo/owl";

export const useRouterParamsChecker = () => {
    const component = useComponent();
    const router = usePosRouter();
    const pos = usePos();
    const routeParams = registry.category("pos_pages").get(component.constructor.name);
    const params = routeParams.params;

    if (params.orderUuid) {
        const order = pos.models["pos.order"].getBy("uuid", router.state.params.orderUuid);
        if (!order || order.finalized !== params.orderFinalized) {
            const params = pos.defaultPage;
            router.navigate(params.page, params.params);
        }
    }
};
