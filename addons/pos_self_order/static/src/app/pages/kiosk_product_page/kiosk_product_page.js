import {
    Component,
    onWillUnmount,
    useState,
    useSubEnv,
    useRef,
    onMounted,
    onPatched,
} from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { KioskAttributeSelection } from "@pos_self_order/app/components/kiosk_attribute_selection/attribute_selection";
import { KioskQuantityWidget } from "@pos_self_order/app/components/kiosk_quantity/quantity_widget";
import { computeProductPrice } from "../../services/card_utils";

export class KioskProductPage extends Component {
    static template = "pos_self_order.KioskProductPage";
    static components = { KioskAttributeSelection, KioskQuantityWidget };
    static props = ["productTemplate"];

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");

        if (!this.props.productTemplate) {
            this.router.navigate("product_list");
            return;
        }

        const editedLine = this.selfOrder.editedLine;
        useSubEnv({ selectedValues: {} });

        this.selfOrder.lastEditedProductId = this.props.productTemplate.id;
        this.state = useState({
            qty: editedLine ? editedLine.qty : 1,
            selectedValues: this.env.selectedValues,
            topShadowOpacity: 0,
            bottomShadowOpacity: 1,
        });

        this.scrollContainerRef = useRef("scrollContainer");

        onMounted(() => {
            this.updateShadows();
            if (this.scrollContainerRef.el) {
                this.scrollContainerRef.el.addEventListener(
                    "scroll",
                    this.updateShadows.bind(this)
                );
                window.addEventListener("resize", this.updateShadows.bind(this));
            }
            setTimeout(() => this.updateShadows(), 100);
        });

        onPatched(() => {
            this.updateShadows();
        });

        onWillUnmount(() => {
            this.selfOrder.editedLine = null;
            if (this.scrollContainerRef.el) {
                this.scrollContainerRef.el.removeEventListener(
                    "scroll",
                    this.updateShadows.bind(this)
                );
                window.removeEventListener("resize", this.updateShadows.bind(this));
            }
        });
    }

    updateShadows() {
        const container = this.scrollContainerRef.el;
        if (!container) {
            return;
        }

        const { scrollTop, scrollHeight, clientHeight } = container;
        this.state.topShadowOpacity = scrollTop > 0 ? 1 : 0;
        this.state.bottomShadowOpacity = scrollTop + clientHeight < scrollHeight ? 1 : 0;
    }

    get productTemplate() {
        return this.props.productTemplate;
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
        if (!this.productTemplate.attribute_line_ids.length) {
            return false;
        }
        const selection = this.state.selectedValues[this.productTemplate.id];
        if (!selection) {
            return true;
        }
        return selection.hasMissingAttributeValues(this.productTemplate.attribute_line_ids);
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
        return computeProductPrice(
            this.selfOrder,
            this.props.productTemplate,
            this.getSelectedAttributesValues(),
            this.state.qty
        );
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
            this.getSelectedAttributesValues()
        );
        this.router.back();
    }
}
