import { Component, proxy, types, useProps } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { ProductInterface } from "@pos_self_order/app/components/product_interface/product_interface";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";

export class OptionalProductPage extends Component {
    static template = "pos_self_order.OptionalProductPage";
    static components = { ProductCard, ProductInterface };

    props = useProps({
        productTemplate: types.instanceOf(ProductTemplate),
    });

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");

        if (!this.productTemplate || !this.optionalProducts.length) {
            this.goBack();
            return;
        }

        this.state = proxy({
            optionalProductQtyById: history.state?.optionalProductQtys || {},
        });
    }

    get productTemplate() {
        return this.props.productTemplate;
    }

    get optionalProducts() {
        return this.productTemplate.pos_optional_product_ids.filter(
            (product) => product.self_order_available && this.selfOrder.isProductAvailable(product)
        );
    }

    get isOptionalProductSelected() {
        return Object.values(this.state.optionalProductQtyById).some((qty) => qty > 0);
    }

    get productCardClasses() {
        return `btn btn-light d-flex flex-row-reverse flex-md-column align-items-center w-100 py-2 px-3
            rounded-4 shadow-sm overflow-hidden border-2 text-md-center text-start border-transparent`;
    }

    /**
     * Counts the selected optional product and returns the history state for
     * navigating to its configuration page.
     */
    onClickOptionalProduct(product) {
        const optionalProductQtyById = this.state.optionalProductQtyById;
        const newHistoryState = {
            redirectPage: "optional_product",
            params: { id: this.productTemplate.id },
            state: {
                optionalProductQtys: { ...optionalProductQtyById },
            },
        };
        this.state.optionalProductQtyById[product.id] =
            (optionalProductQtyById[product.id] || 0) + 1;
        return newHistoryState;
    }

    goBack() {
        this.router.navigate("product_list");
    }
}
