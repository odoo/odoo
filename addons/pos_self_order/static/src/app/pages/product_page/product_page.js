import { Component, onWillUnmount, useState, useSubEnv, useRef, onMounted } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { AttributeSelection } from "@pos_self_order/app/components/attribute_selection/attribute_selection";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";

export class ProductPage extends Component {
    static template = "pos_self_order.ProductPage";
    static components = { AttributeSelection };
    static props = ["productTemplate"];

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
        this.state = useState({
            qty: editedLine ? editedLine.qty : 1,
            selectedValues: this.env.selectedValues,
            topShadowOpacity: 0,
            bottomShadowOpacity: 0,
            showStickyTitle: false,
        });
        this.productNameRef = useRef("productName");
        this.scrollContainerRef = useRef("scrollContainer");
        this.scrollShadow = useScrollShadow(this.scrollContainerRef);

        onMounted(() => {
            const productNameEl = this.productNameRef.el;
            if (productNameEl) {
                this.observer = new IntersectionObserver(
                    ([entry]) => {
                        this.state.showStickyTitle = !entry.isIntersecting;
                    },
                    {
                        root: null,
                        threshold: 0,
                    }
                );
                this.observer.observe(productNameEl);
            }
        });

        onWillUnmount(() => {
            this.selfOrder.editedLine = null;

            if (this.observer) {
                this.observer.unobserve(this.productNameRef.el);
            }
        });
    }

    get productTemplate() {
        return this.props.productTemplate;
    }

    shouldShowMissingDetails() {
        const el = this.scrollContainerRef?.el;
        if (!el) {
            return false;
        }
        return (
            el.scrollHeight > el.clientHeight && this.productTemplate.attribute_line_ids.length > 1
        );
    }

    changeQuantity(increase) {
        const currentQty = this.state.qty;

        if (!increase && currentQty === 1) {
            return;
        }

        return increase ? this.state.qty++ : this.state.qty--;
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
        const productTmplAttrModel = this.selfOrder.models["product.template.attribute.value"];
        const attributeIds = this.getSelectedAttributesValues();
        const attributes = productTmplAttrModel.readMany(attributeIds);
        const priceExtra = attributes.reduce((sum, attr) => sum + attr.price_extra, 0);
        const price = this.props.productTemplate.getPrice(
            this.selfOrder.currentOrder.pricelist_id,
            1,
            priceExtra
        );
        const taxDetails = this.props.productTemplate.getTaxDetails({
            overridedValues: { price_unit: price, quantity: this.state.qty },
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

        this.goBack();
    }

    goBack() {
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

    /*
    // TODO
    get editableProductLine() {
        const order = this.selfOrder.currentOrder;
        return !(
            this.selfOrder.editedLine &&
            this.selfOrder.editedLine.uuid &&
            order.lastChangesSent[this.selfOrder.editedLine.uuid]
        );
    }*/
}
