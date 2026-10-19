import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";
import { formatMonetary } from "@web/views/fields/formatters";

class ProductSnapshotOptionPlugin extends Plugin {
    static id = "productSnapshot";
    static shared = ["priceSelector", "getPricelistPrice", "getPriceEl"];

    priceSelector() {
        return ".s_product_snapshot_price";
    }

    resources = {
        builder_actions: {
            SelectPricelistAction,
        },
    };

    async getPricelistPrice(pricelistId, productId) {
        return this.services.orm.call(
            "product.pricelist.item",
            "mass_mailing_get_item_prices",
            [pricelistId],
            {
                product_id: productId,
            }
        );
    }

    getPriceEl(el) {
        return el.querySelector(this.priceSelector());
    }
}

class ProductSnapshotOption extends BaseOptionComponent {
    static id = "product_snapshot_option";
    static template = "mass_mailing_sale.productSnapshotOption";

    async setup() {
        super.setup();
        this.state = proxy({ domain: false });
        this.state.domain = await this.getPricelistDomain(this.env.getEditingElement().dataset.id);
    }

    async getPricelistDomain(product_id) {
        if (!product_id) {
            return false;
        }
        return await this.services.orm.call(
            "product.pricelist.item",
            "mass_mailing_get_pricelist_domain",
            [NaN, Number(product_id)]
        );
    }

    getElementDataModel() {
        return this.env.getEditingElement().dataset.model;
    }
}

class SelectPricelistAction extends BuilderAction {
    static dependencies = ["builderOptions", "recordSnapshot", "productSnapshot"];
    static id = "selectPricelistAction";

    getValue({ editingElement: el }) {
        const priceEl = this.dependencies.productSnapshot.getPriceEl(el);
        if (priceEl && priceEl.dataset.pricelistId) {
            return JSON.stringify({
                id: parseInt(priceEl.dataset.pricelistId),
                display_name: priceEl.dataset.pricelistDisplayName || "",
                name: priceEl.dataset.pricelistName || "",
            });
        }
        return;
    }

    async apply({ editingElement: el, value }) {
        value = JSON.parse(value);
        const priceEl = el.querySelector(this.dependencies.productSnapshot.priceSelector());
        if (!priceEl) {
            return;
        }

        const pricelistPrice = await this.dependencies.productSnapshot.getPricelistPrice(
            value.id,
            Number(el.dataset.id)
        );
        const fragmentArgs = {
            currentPrice: formatMonetary(pricelistPrice.current_price, {
                currencyId: pricelistPrice.currency_id,
                trailingZeros: false,
            }),
        };
        if (pricelistPrice.base_price > pricelistPrice.current_price) {
            fragmentArgs.strickenPrice = formatMonetary(pricelistPrice.base_price, {
                currencyId: pricelistPrice.currency_id,
                trailingZeros: false,
            });
        }

        const fragment = renderToElement(
            "mass_mailing_sale.s_product_snapshot_price",
            fragmentArgs
        );
        fragment.dataset.pricelistId = value.id;
        fragment.dataset.pricelistDisplayName = value.display_name;
        fragment.dataset.pricelistName = value.name;

        // Carry over class list and style from old element
        fragment.classList.add(...priceEl.classList);
        fragment.style.cssText = priceEl.style.cssText;

        priceEl.replaceWith(fragment);
    }

    async clean({ editingElement: el }) {
        const priceEl = this.dependencies.productSnapshot.getPriceEl(el);
        const product = await this.services.orm.read(
            "product.product",
            [Number(el.dataset.id)],
            ["lst_price", "currency_id"]
        );
        const fragment = renderToElement("mass_mailing_sale.s_product_snapshot_price", {
            currentPrice: formatMonetary(product[0].lst_price, {
                currencyId: product[0].currency_id[0],
                trailingZeros: false,
            }),
        });
        fragment.classList.add(...priceEl.classList);
        fragment.style.cssText = priceEl.style.cssText;

        priceEl.replaceWith(fragment);
    }
}

registry
    .category("mass_mailing-plugins")
    .add(ProductSnapshotOptionPlugin.id, ProductSnapshotOptionPlugin);
registry.category("mass_mailing-options").add(ProductSnapshotOption.id, ProductSnapshotOption);
