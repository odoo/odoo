import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
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
            "product.pricelist",
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
        this.state = proxy({ isPricelistAvailable: false });
        this.state.isPricelistAvailable = await this.isPricelistAvailable(
            this.env.getEditingElement().dataset.id
        );
    }

    async isPricelistAvailable(product_id) {
        if (!product_id) {
            return false;
        }
        return await user.hasGroup("product.group_product_pricelist");
    }
}

class SelectPricelistAction extends BuilderAction {
    static dependencies = ["productSnapshot", "history"];
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

    async apply({ editingElement: el, value, isPreviewing }) {
        value = JSON.parse(value);
        const priceEl = this.dependencies.productSnapshot.getPriceEl(el);
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
        if (pricelistPrice.price_before_discount > pricelistPrice.current_price) {
            fragmentArgs.strickenPrice = formatMonetary(pricelistPrice.price_before_discount, {
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
        if (!isPreviewing) {
            this.dependencies.history.commit();
        }
    }

    async clean({ editingElement: el, isPreviewing }) {
        const priceEl = this.dependencies.productSnapshot.getPriceEl(el);
        if (!priceEl) {
            return;
        }
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
        if (!isPreviewing) {
            this.dependencies.history.commit();
        }
    }
}

registry
    .category("mass_mailing-plugins")
    .add(ProductSnapshotOptionPlugin.id, ProductSnapshotOptionPlugin);
registry.category("mass_mailing-options").add(ProductSnapshotOption.id, ProductSnapshotOption);
