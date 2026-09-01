import { Component, useProps, t } from "@odoo/owl";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { ProductProduct } from "@point_of_sale/app/models/product_product";
import {
    MAX_SELF_ORDER_LINE_QTY,
    useSelfOrder,
} from "@pos_self_order/app/services/self_order_service";
import { flyToCart } from "@pos_self_order/app/utils/ui_animations";
import { formatProductName } from "@pos_self_order/app/utils";
import { ProductInfoPopup } from "../product_info_popup/product_info_popup";

export class ProductCard extends Component {
    static template = "pos_self_order.ProductCard";

    props = useProps({
        product: t.or([t.instanceOf(ProductProduct), t.instanceOf(ProductTemplate)]),
        class: t.string().optional(),
        qty: t.number().optional(),
        onClickCallback: t.function().optional(),
        hidePrice: t.boolean().optional(false),
        selectProduct: t.function().optional(), // custom handler to override the default selectProduct method
    });

    setup() {
        this.selfOrder = useSelfOrder();
    }

    isProductAtMaxQty() {
        const tmplId = this.productTmpl.id;
        return this.selfOrder.currentOrder?.lines.some(
            (l) => l.product_id?.product_tmpl_id?.id === tmplId && l.qty >= MAX_SELF_ORDER_LINE_QTY
        );
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
        this.selfOrder.dialog.add(ProductInfoPopup, {
            productTemplate: this.productTmpl,
        });
    }

    formatProductName(product) {
        return formatProductName(product);
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
            const { show, selectedCombos } = this.productTmpl.showComboSelectionPage();
            if (show) {
                router.navigate("combo_selection", { id: product.id }, historyState);
                return;
            }

            if (!this.isProductAtMaxQty()) {
                flyToCart(target);
            }
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

        const isConfigurable = product.isConfigurableForSelfOrder;
        if (this.selfOrder.ordering && !isConfigurable) {
            if (!this.isProductAtMaxQty()) {
                flyToCart(target);
            }
            this.selfOrder.addToCart(product, 1);
        }

        if (isConfigurable) {
            router.navigate("product", { id: product.id }, historyState);
        } else if (product.pos_optional_product_ids.length && !historyState.redirectPage) {
            router.navigate("optional_product", { id: product.id }, historyState);
        }
    }
}
