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
        const showConfirm = this.el.dataset.confirmedorders === "true";
        const view = this.el.dataset.viewchange || "list";
        const limit = parseInt(this.el.dataset.limitchange || "3", 10);

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
        container.replaceChildren(content);

        if (mapped.length >= limit) {
            this._addLoadMoreButton(container);
        }
    }

    _addLoadMoreButton(container) {
        const btnWrapper = document.createElement("div");
        btnWrapper.className = "text-center mt-3";

        const btn = document.createElement("button");
        btn.className = "btn btn-primary load-more-btn";
        btn.textContent = "Load More";

        btn.addEventListener("click", () => {
            this.loadOrders();
        });

        btnWrapper.appendChild(btn);
        container.appendChild(btnWrapper);
    }
}

registry.category("public.interactions").add("sale_order_display", SaleOrderDisplay);
registry.category("public.interactions.edit").add("sale_order_display",{Interaction:SaleOrderDisplay});
