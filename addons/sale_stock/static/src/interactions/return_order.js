import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { ReturnOrderDialog } from "@sale_stock/return_order_dialog/return_order_dialog";

export class PortalReturnOrder extends Interaction {
    static selector = ".o_portal_sale_sidebar";
    dynamicContent = {".o_return_button": { "t-on-click": this.onClickReturnButton }};

    async onClickReturnButton(ev) {
        const orderId = parseInt(ev.currentTarget.dataset.saleOrderId);
        const accessToken = new URLSearchParams(window.location.search).get("access_token");
        if (!orderId || !accessToken) return;

        this.services.dialog.add(ReturnOrderDialog, {
            saleOrderId: orderId,
            accessToken: accessToken,
        })
    }

}

registry.category("public.interactions").add("sale_stock.return_order", PortalReturnOrder);
