/** @odoo-module */
import { useSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { ProductCatalogOrderLine } from "./order_line/order_line";

export class ProductCatalogKanbanRecord extends KanbanRecord {
    static template = "ProductCatalogKanbanRecord";
    static components = {
        ...KanbanRecord.components,
        ProductCatalogOrderLine,
    };

    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.debouncedUpdateQuantity = useDebounced(this._updateQuantity, 500, {
            execBeforeUnmount: true,
        });

        useSubEnv({
            currencyId: this.props.record.context.product_catalog_currency_id,
            orderId: this.props.record.context.product_catalog_order_id,
            orderResModel: this.props.record.context.product_catalog_order_model,
            digits: this.props.record.context.product_catalog_digits,
            displayUoM: this.props.record.context.display_uom,
            precision: this.props.record.context.precision,
            productId: this.props.record.resId,
            addProduct: this.addProduct.bind(this),
            removeProduct: this.removeProduct.bind(this),
            increaseQuantity: this.increaseQuantity.bind(this),
            setQuantity: this.setQuantity.bind(this),
            decreaseQuantity: this.decreaseQuantity.bind(this),
        });
    }

    get orderLineComponent() {
        return ProductCatalogOrderLine;
    }

    get productCatalogData() {
        return this.props.record.productCatalogData;
    }

    onGlobalClick(ev) {
        // avoid a concurrent update when clicking on the buttons (that are inside the record)
        if (ev.target.closest(".o_product_catalog_cancel_global_click")) {
            return;
        }
        if (this.productCatalogData.quantity === 0) {
            this.addProduct();
        } else {
            this.increaseQuantity();
        }
    }

    //--------------------------------------------------------------------------
    // Data Exchanges
    //--------------------------------------------------------------------------

    async _updateQuantity() {
        const price = await this._updateQuantityAndGetPrice();
        this.productCatalogData.price = parseFloat(price);
    }

    _updateQuantityAndGetPrice() {
        return this.rpc("/product/catalog/update_order_line_info", {
            order_id: this.env.orderId,
            product_id: this.env.productId,
            quantity: this.productCatalogData.quantity,
            res_model: this.env.orderResModel,
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    updateQuantity(quantity) {
        if (this.productCatalogData.readOnly) {
            return;
        }
        this.productCatalogData.quantity = quantity || 0;
        this.debouncedUpdateQuantity();
    }

    /**
     * Add the product to the order
     */
    addProduct(qty=1) {
        this.updateQuantity(qty);
    }

    /**
     * Remove the product to the order
     */
    removeProduct() {
        this.updateQuantity(0);
    }

    /**
     * Increase the quantity of the product on the order line.
     */
    increaseQuantity(qty=1) {
        this.updateQuantity(this.productCatalogData.quantity + qty);
    }

    /**
     * Set the quantity of the product on the order line.
     *
     * @param {Event} event
     */
    setQuantity(event) {
        this.updateQuantity(parseFloat(event.target.value));
    }

    /**
     * Decrease the quantity of the product on the order line.
     */
    decreaseQuantity() {
        this.updateQuantity(parseFloat(this.productCatalogData.quantity - 1));
    }
}
