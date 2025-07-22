/** @odoo-module **/

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { renderToFragment } from "@web/core/utils/render";

export class SaleOrderDisplay extends Interaction {
    static selector = ".s_sale_order_display";

    dynamicContent = {
        ".load-more-btn": {
            "t-on-click": () => this.loadOrders(),
        },
    };

    setup() {
        this.orm = this.env.services.orm;
        this.offset = 0;
        this.orders = [];
        this.loadOrders({ reset: true });
    }

    async loadOrders({ reset = false } = {}) {
        const showConfirm = this.el.dataset.showConfirm === "true";
        const view = this.el.dataset.view || "list";
        const limit = parseInt(this.el.dataset.limit || "3", 10);

        if (reset) {
            this.offset = 0;
            this.orders = [];
        }

        const domain = showConfirm
            ? [["state", "=", "sale"]]
            : [["state", "in", ["sale", "draft", "sent"]]];

        const result = await this.orm.searchRead(
            "sale.order",
            domain,
            ["name", "partner_id", "state"],
            { offset: this.offset, limit, order: "id asc" }
        );

        const mapped = result.map((r) => ({
            name: r.name,
            partner_name: r.partner_id?.[1] || "",
            state: r.state,
        }));

        this.orders.push(...mapped);
        this.offset += mapped.length;

        const templateName = view === "list"
            ? "website.s_sale_order_display_list"
            : "website.s_sale_order_display_card";

        const content = await renderToFragment(templateName, {
            sale_orders: this.orders,
        });

        const container = this.el.querySelector(".container");

        container.querySelectorAll(".sale-order-list, .sale-order-card").forEach(node => node.remove());

        const buttonWrapper = container.querySelector(".load-btn-class");
        container.insertBefore(content, buttonWrapper);

        if (mapped.length < limit) {
            const btn = this.el.querySelector(".load-more-btn")
            if (btn) {
                btn.classList.add("d-none")
            }
        }
    }

}

const HideInEditModeMixin = (Base) => class extends Base {
    dynamicContent = {
        ".load-more-btn": { "t-att-class": () => ({ "d-none": true }) }
    };
};


registry.category("public.interactions").add("sale_order_display", SaleOrderDisplay);
registry.category("public.interactions.edit").add("sale_order_display", { Interaction: SaleOrderDisplay, mixin: HideInEditModeMixin });
