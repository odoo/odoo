import { Component, props, t } from "@odoo/owl";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { flyToCart } from "@pos_self_order/app/utils/ui_animations";
import { useService } from "@web/core/utils/hooks";
import { formatProductName } from "@pos_self_order/app/utils";
import { ProductInfoPopup } from "../product_info_popup/product_info_popup";

export class ProductCard extends Component {
    static template = "pos_self_order.ProductCard";

    props = props({
        product: t.or([t.instanceOf(ProductProduct), t.instanceOf(ProductTemplate)]),
        class: t.string().optional(),
        qty: t.number().optional(),
        onClickCallback: t.function().optional(),
        hidePrice: t.boolean().optional(false),
        selectProduct: t.function().optional(), // custom handler to override the default selectProduct method
    });

    setup() {
        this.selfOrder = useSelfOrder();
        this.dialog = useService("dialog");
    }

    get isProductAvailable() {
        return this.selfOrder.isProductAvailable(this.props.product);
    }

    get isProductSnoozed() {
        return this.selfOrder.isProductSnoozed(this.props.product);
    }

    get productTmpl() {
        const product = this.props.product;
        if (product instanceof ProductProduct) {
            return product.product_tmpl_id;
        }
        return product;
    }

    displayProductInfo() {
        this.dialog.add(ProductInfoPopup, {
            productTemplate: this.productTmpl,
        });
    }

    formatProductName(product) {
        return formatProductName(product);
    }

    showComboSelectionPage() {
        const product = this.productTmpl;
        const selectedCombos = [];
        for (const combo of product.combo_ids) {
            const { combo_item_ids } = combo;
            if (
                combo_item_ids.length > 1 ||
                combo.qty_max > 1 ||
                this.selfOrder.isProductConfigurable(combo_item_ids[0]?.product_id)
            ) {
                return { show: true, selectedCombos: [] };
            }
            const item = this.selfOrder.models["product.combo.item"].get(combo_item_ids[0].id);
            selectedCombos.push({
                combo_item_id: item,
                qty: 1,
                configuration: {
                    attribute_custom_values: [],
                    attribute_value_ids: [],
                    price_extra: 0,
                },
            });
        }
        return { show: false, selectedCombos };
    }

    selectProduct(target) {
        const product = this.props.product;
        if (this.props.selectProduct) {
            return this.props.selectProduct(product);
        }

        if (!product.self_order_available || !this.isProductAvailable || this.isProductSnoozed) {
            return;
        }

        const historyState =
            (this.props.onClickCallback && this.props.onClickCallback(product)) || {};
        const router = this.selfOrder.router;
        if (product.isCombo()) {
            const { show, selectedCombos } = this.showComboSelectionPage();
            if (show) {
                router.navigate("combo_selection", { id: product.id }, historyState);
                return;
            }

            flyToCart(target);
            this.selfOrder.addToCart(
                product,
                1,
                "",
                {},
                {},
                selectedCombos.map((combo) => ({
                    ...combo,
                    qty: 1,
                }))
            );
            return;
        }

        const isConfigurable = this.selfOrder.isProductConfigurable(product);
        if (this.selfOrder.ordering && !isConfigurable) {
            flyToCart(target);
            this.selfOrder.addToCart(product, 1);
        }

        if (isConfigurable) {
            router.navigate("product", { id: product.id }, historyState);
        } else if (product.pos_optional_product_ids.length && !historyState.redirectPage) {
            router.navigate("optional_product", { id: product.id }, historyState);
        }
    }
}
