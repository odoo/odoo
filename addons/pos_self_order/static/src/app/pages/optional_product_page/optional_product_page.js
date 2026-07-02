import { Component, props, proxy, types } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { ProductInterface } from "@pos_self_order/app/components/product_interface/product_interface";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";

export class OptionalProductPage extends Component {
    static template = "pos_self_order.OptionalProductPage";
    static components = { ProductCard, ProductInterface };

    props = props({
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
        return this.productTemplate.pos_optional_product_ids;
    }

    get isOptionalProductSelected() {
        return Object.values(this.state.optionalProductQtyById).some((qty) => qty > 0);
    }

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
