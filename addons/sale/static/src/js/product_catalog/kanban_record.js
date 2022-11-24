/** @odoo-module */
import { useState, useSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { useDebounced } from "@web/core/utils/timing";
import { ProductCatalogSOL } from "./sale_order_line/sale_order_line"

export class ProductCatalogKanbanRecord extends KanbanRecord {
    static template = "sale.ProductCatalogKanbanRecord";
    static components = {...KanbanRecord.components, ProductCatalogSOL};

    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.state = useState({
            price:  this.props.record.productCatalogData.price,
            quantity: this.props.record.productCatalogData.quantity || 0,
        });
        this.debouncedUpdateQuantity = useDebounced(this._updateQuantity, 500);

        useSubEnv({
            currencyId: this.props.record.context.product_catalog_currency_id,
            orderId: this.props.record.context.product_catalog_order_id,
            productId: this.record.id.raw_value,
            addProduct: this.addProduct.bind(this),
            removeProduct: this.removeProduct.bind(this),
            increaseQuantity: this.increaseQuantity.bind(this),
            setQuantity: this.setQuantity.bind(this),
            decreaseQuantity: this.decreaseQuantity.bind(this),
        });
    }

    onGlobalClick(ev) {
        // avoid a concurrent update when clicking on the buttons (that are inside the record)
        if (ev.target.closest(".o_sale_product_catalog_cancel_global_click")) {
            return;
        }
        this.increaseQuantity();
    }

    //--------------------------------------------------------------------------
    // Data Exchanges
    //--------------------------------------------------------------------------

    async _updateQuantity() {
        const price = await this.rpc("/sales/catalog/update_sale_order_line_info", {
            order_id: this.env.orderId,
            product_id: this.env.productId,
            quantity: this.state.quantity,
        })
        // Force a reload of the page to remove a product from the view in the case a filter is
        // applied.
        if (this.state.quantity === 0) {
            this.props.record.model.load();
        }
        this.state.price = parseFloat(price);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Add the product to the order
     */
    addProduct() {
        if (this.props.record.productCatalogData.readOnly) return;
        this.state.quantity = 1;
        this.debouncedUpdateQuantity();
    }

    /**
     * Remove the product to the order
     */
    removeProduct() {
        if (this.props.record.productCatalogData.readOnly) return;
        this.state.quantity = 0;
        this.debouncedUpdateQuantity();
    }

    /**
     * Increase the quantity of the product on the sale order line.
     */
    increaseQuantity() {
        if (this.props.record.productCatalogData.readOnly) return;
        this.state.quantity += 1;
        this.debouncedUpdateQuantity();
    }

    /**
     * Set the quantity of the product on the sale order line.
     *
     * @param {Event} event
     */
    setQuantity(event) {
        if (this.props.record.productCatalogData.readOnly) return;
        this.state.quantity = parseFloat(event.target.value);
        this.debouncedUpdateQuantity();
    }

    /**
     * Decrease the quantity of the product on the sale order line.
     */
    decreaseQuantity() {
        if (this.props.record.productCatalogData.readOnly) return;
        this.state.quantity -= 1;
        this.debouncedUpdateQuantity();
    }

}
