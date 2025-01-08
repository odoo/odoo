import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { rpc } from "@web/core/network/rpc";

export class SaleUpdateLineButton extends Interaction {
    static selector = ".o_portal_sale_sidebar";
    dynamicContent = {
        "a.js_update_line_json": {
            "t-on-click.prevent.withTarget": this.onClickOptionQuantityButton,
        },
        "a.js_add_optional_products": {
            "t-on-click.prevent.withTarget": this.onClickAddOptionalProduct,
        },
        ".js_quantity": {
            "t-on-change.prevent.withTarget": this.onChangeOptionQuantity,
        },
    };

    setup() {
        this.orderDetail = this.el.querySelector('table#sales_order_table').dataset;
    }

    callUpdateLineRoute(orderId, params) {
        return rpc("/my/orders/" + orderId + "/update_line_dict", params);
    }

    callAddOptionRoute(orderId, optionId, params) {
        return rpc("/my/orders/" + orderId + "/add_option/" + optionId, params);
    }

    refreshOrderUI(data) {
        window.location.reload();
    }

    async onChangeOptionQuantity(ev, currentTargetEl) {
        const quantity = parseInt(currentTargetEl.value);
        const data = await this.waitFor(this.callUpdateLineRoute(this.orderDetail.orderId, {
            'access_token': this.orderDetail.token,
            'input_quantity': quantity >= 0 ? quantity : false,
            'line_id': currentTargetEl.dataset.lineId,
        }));
        this.refreshOrderUI(data);
    }

    async onClickOptionQuantityButton(ev, currentTargetEl) {
        const data = await this.waitFor(this.callUpdateLineRoute(this.orderDetail.orderId, {
            'access_token': this.orderDetail.token,
            'line_id': currentTargetEl.dataset.lineId,
            'remove': currentTargetEl.dataset.remove,
            'unlink': currentTargetEl.dataset.unlink,
        }));
        this.refreshOrderUI(data);
    }

    async onClickAddOptionalProduct(ev, currentTargetEl) {
        currentTargetEl.style.setProperty('pointer-events', 'none');
        const data = await this.waitFor(this.callAddOptionRoute(this.orderDetail.orderId, currentTargetEl.dataset.optionId, {
            'access_token': this.orderDetail.token,
        }));
        this.refreshOrderUI(data);
    }
}

registry
    .category("public.interactions")
    .add("sale_management.sale_update_line_button", SaleUpdateLineButton);
