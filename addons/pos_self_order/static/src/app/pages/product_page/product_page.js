import { useSubEnv } from "@web/owl2/utils";
import { Component, proxy, useProps, t } from "@odoo/owl";
import {
    MAX_SELF_ORDER_LINE_QTY,
    useSelfOrder,
} from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { AttributeSelection } from "@pos_self_order/app/components/attribute_selection/attribute_selection";
import { ProductInterface } from "@pos_self_order/app/components/product_interface/product_interface";
import {
    getProductVariantByAttributes,
    getAttributeValues,
    getAttributeValuesExtraPrice,
} from "@pos_self_order/app/services/card_utils";
import { shouldShowMissingDetails } from "../../utils";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";

export class ProductPage extends Component {
    static template = "pos_self_order.ProductPage";
    static components = { AttributeSelection, ProductInterface };
    props = useProps({ productTemplate: t.instanceOf(ProductTemplate) });

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");

        if (!this.props.productTemplate) {
            this.goBack();
            return;
        }

        const editedLine = this.selfOrder.editedLine;
        useSubEnv({ selectedValues: {} });

        this.selfOrder.lastEditedProductId = this.props.productTemplate.id;
        this.state = proxy({
            qty: editedLine ? editedLine.qty : 1,
            selectedValues: this.env.selectedValues,
        });
    }

    get productTemplate() {
        return this.props.productTemplate;
    }

    shouldShowMissingDetails() {
        return shouldShowMissingDetails(this.productTemplate, this.state.selectedValues);
    }

    changeQuantity(increase) {
        const currentQty = this.state.qty;

        if (!increase && currentQty === 1) {
            return;
        }
        if (increase && this.isQuantityAtMaximum()) {
            this.selfOrder.showMaxQtyNotification();
            return;
        }

        const result = increase ? this.state.qty++ : this.state.qty--;
        if (increase && this.isQuantityAtMaximum()) {
            this.selfOrder.showMaxQtyNotification();
        }
        return result;
    }

    isQuantityAtMaximum() {
        return this.state.qty >= MAX_SELF_ORDER_LINE_QTY;
    }

    isProductAvailable() {
        return this.props.productTemplate.self_order_available;
    }

    get showQtyButtons() {
        return this.isProductAvailable();
    }

    hasMissingAttributeValues() {
        const selection = this.state.selectedValues[this.productTemplate.id];
        if (!selection) {
            return true;
        }
        return Boolean(selection.getMissingAttributeValue(this.productTemplate.attribute_line_ids));
    }

    isAddToCartEnabled() {
        return (
            this.isProductAvailable() &&
            !this.hasMissingAttributeValues() &&
            !this.isArchivedCombination()
        );
    }

    isArchivedCombination() {
        if (this.hasMissingAttributeValues()) {
            return false;
        }
        const selection = this.state.selectedValues[this.productTemplate.id];
        if (!selection) {
            return false;
        }
        const variantAttributeValueIds = selection
            .getAllSelectedAttributeValuesIds()
            .map((attr) => Number(attr));
        return this.props.productTemplate._isArchivedCombination(variantAttributeValueIds);
    }

    getProductPrice() {
        const attributeIds = this.getSelectedAttributesValues();

        const productVariant = getProductVariantByAttributes(
            this.selfOrder.models,
            this.props.productTemplate,
            attributeIds
        );

        const priceExtra = getAttributeValuesExtraPrice(
            getAttributeValues(attributeIds, this.selfOrder.models)
        );

        const order = this.selfOrder.currentOrder;
        const pricelist = order.pricelist_id;
        const price = this.props.productTemplate.getPrice(
            pricelist,
            1,
            priceExtra,
            false,
            productVariant
        );
        const product = productVariant || this.props.productTemplate;
        const fiscalPosition = order.fiscal_position_id;
        const taxDetails = product.getTaxDetails({
            overridedValues: {
                price,
                fiscalPosition,
                quantity: this.state.qty,
            },
        });
        return this.selfOrder.isTaxesIncludedInPrice()
            ? taxDetails.total_included
            : taxDetails.total_excluded;
    }

    getSelectedAttributesValues() {
        return (
            this.state.selectedValues[
                this.productTemplate.id
            ]?.getAllSelectedAttributeValuesIds() || []
        );
    }

    addToCart() {
        if (!this.isAddToCartEnabled()) {
            return;
        }
        this.selfOrder.addToCart(
            this.props.productTemplate,
            this.state.qty,
            "",
            this.getSelectedAttributesValues(),
            this.state.selectedValues[this.productTemplate.id]?.getAllCustomValues()
        );

        const historyState = history.state || {};
        if (this.productTemplate.pos_optional_product_ids.length && !historyState.redirectPage) {
            return this.router.navigate("optional_product", { id: this.productTemplate.id });
        }

        // We came from the optional product page to configure this product: account for it
        // in the snapshot it left behind, so its badge matches what is now in the cart.
        const qtys = historyState.state?.optionalProductQtys;
        if (qtys) {
            qtys[this.productTemplate.id] = (qtys[this.productTemplate.id] || 0) + this.state.qty;
        }
        this.goBack();
    }

    goBack() {
        if (history.state?.redirectPage) {
            const { redirectPage, params, state } = history.state;
            return this.router.navigate(redirectPage, params, state);
        }
        this.router.navigate("product_list");
    }

    scrollUpToRequired() {
        const selection = this.state.selectedValues[this.productTemplate.id];
        const missingAttribute = selection?.getMissingAttributeValue(
            this.productTemplate.attribute_line_ids
        );
        document
            .getElementById(missingAttribute?.attribute_id?.id)
            ?.scrollIntoView({ behavior: "smooth" });
    }
}
