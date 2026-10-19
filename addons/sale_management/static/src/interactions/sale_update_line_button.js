import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { rpc } from "@web/core/network/rpc";

export class SaleUpdateLineButton extends Interaction {
    static selector = ".o_portal_sale_sidebar";
    dynamicContent = {
        "a.js_update_line_json": {
            "t-on-click.prevent": this.onUpdateLineClick,
        },
        ".js_quantity": {
            "t-on-change.prevent": this.onQuantityChange,
        },
    };

    setup() {
        this.orderDetail = this.el.querySelector("table#sales_order_table").dataset;
    }

    /**
     * @param {number} orderId
     * @param {Object} params
     */
    callUpdateLineRoute(orderId, params) {
        return rpc("/my/orders/" + orderId + "/update_line_dict", params);
    }

    refreshOrderUI() {
        window.location.reload();
    }

    /**
     * @param {MouseEvent} ev
     */
    async onQuantityChange(ev) {
        const currentTarget = ev.currentTarget;
        const quantity = parseInt(currentTarget.value);
        await this.waitFor(this.callUpdateLineRoute(this.orderDetail.orderId, {
            "access_token": this.orderDetail.token,
            "input_quantity": quantity >= 0 ? quantity : false,
            "line_id": currentTarget.dataset.lineId,
        }));
        this.refreshOrderUI();
    }

    /**
     * @param {MouseEvent} ev
     */
    async onUpdateLineClick(ev) {
        const currentTarget = ev.currentTarget;
        await this.waitFor(this.callUpdateLineRoute(this.orderDetail.orderId, {
            "access_token": this.orderDetail.token,
            "line_id": currentTarget.dataset.lineId,
            "remove": currentTarget.dataset.remove,
        }));
        this.refreshOrderUI();
    }
}

registry
    .category("public.interactions")
    .add("sale_management.sale_update_line_button", SaleUpdateLineButton);
