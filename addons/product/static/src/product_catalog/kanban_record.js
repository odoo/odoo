import { rpc } from "@web/core/network/rpc";
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
        this.debouncedUpdateQuantity = useDebounced(this._updateQuantity, 500, {
            execBeforeUnmount: true,
        });
    }

    get orderLineProps() {
        const record = this.props.record;
        return {
            childField: record.context.child_field,
            code: record.productCatalogData.code,
            currencyId: record.context.product_catalog_currency_id,
            digits: record.context.product_catalog_digits,
            displayUoM: record.context.display_uom,
            isSample: record.productCatalogData.isSample,
            orderId: record.context.product_catalog_order_id,
            orderResModel: record.context.product_catalog_order_model,
            precision: record.context.precision,
            productType: record.productCatalogData.productType,
            price: record.productCatalogData.price,
            productId: record.resId,
            quantity: record.productCatalogData.quantity,
            readOnly: record.productCatalogData.readOnly,
            uomDisplayName: record.productCatalogData.uomDisplayName,
            warning: record.productCatalogData.warning,
            addProduct: this.addProduct.bind(this),
            removeProduct: this.removeProduct.bind(this),
            increaseQuantity: this.increaseQuantity.bind(this),
            setQuantity: this.setQuantity.bind(this),
            decreaseQuantity: this.decreaseQuantity.bind(this),
        };
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
        return rpc(
            "/product/catalog/update_order_line_info",
            this._getUpdateQuantityAndGetPriceParams()
        );
    }

    _getUpdateQuantityAndGetPriceParams() {
        return {
            order_id: this.orderLineProps.orderId,
            product_id: this.orderLineProps.productId,
            quantity: this.productCatalogData.quantity,
            res_model: this.orderLineProps.orderResModel,
            child_field: this.orderLineProps.childField,
        };
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    updateQuantity(quantity, debounce = true) {
        if (this.productCatalogData.readOnly) {
            return;
        }
        this.productCatalogData.quantity = quantity || 0;
        if (debounce) {
            this.debouncedUpdateQuantity();
        } else {
            this._updateQuantity();
        }
    }

    /**
     * Add the product to the order without waiting for the debounce
     */
    addProduct(quantity = 1) {
        this.updateQuantity(quantity, false);
    }

    /**
     * Remove the product to the order
     */
    removeProduct() {
        this.updateQuantity(0, false);
    }

    /**
     * Increase the quantity of the product on the order line.
     */
    increaseQuantity(quantity = 1) {
        this.updateQuantity(this.productCatalogData.quantity + quantity);
    }

    /**
     * Set the quantity of the product on the order line.
     *
     * @param {Event} event
     */
    setQuantity(event) {
        this.updateQuantity(parseFloat(event.target.value), false);
    }

    /**
     * Decrease the quantity of the product on the order line.
     */
    decreaseQuantity() {
        this.updateQuantity(parseFloat(this.productCatalogData.quantity - 1));
    }
}
