/** @odoo-module */
import { useSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { ProductCatalogSOL } from "./sale_order_line/sale_order_line";

export class ProductCatalogKanbanRecord extends KanbanRecord {
    static template = "sale.ProductCatalogKanbanRecord";
    static components = {...KanbanRecord.components, ProductCatalogSOL};

    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.debouncedUpdateQuantity = useDebounced(this._updateQuantity, 500, {
            execBeforeUnmount: true,
        });

        useSubEnv({
            currencyId: this.props.record.context.product_catalog_currency_id,
            orderId: this.props.record.context.product_catalog_order_id,
            digits: this.props.record.context.product_catalog_digits,
            productId: this.props.record.resId,
            addProduct: this.addProduct.bind(this),
            removeProduct: this.removeProduct.bind(this),
            increaseQuantity: this.increaseQuantity.bind(this),
            setQuantity: this.setQuantity.bind(this),
            decreaseQuantity: this.decreaseQuantity.bind(this),
        });
    }

    get productCatalogData() {
        return this.props.record.productCatalogData;
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
            quantity: this.productCatalogData.quantity,
        });
        this.productCatalogData.price = parseFloat(price);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    updateQuantity(quantity) {
        if (this.productCatalogData.readOnly) {
            return;
        }
        this.productCatalogData.quantity = quantity;
        this.debouncedUpdateQuantity();
    }
    /**
     * Add the product to the order
     */
    addProduct() {
        this.updateQuantity(1);
    }

    /**
     * Remove the product to the order
     */
    removeProduct() {
        this.updateQuantity(0);
    }

    /**
     * Increase the quantity of the product on the sale order line.
     */
    increaseQuantity() {
        this.updateQuantity(this.productCatalogData.quantity + 1);
    }

    /**
     * Set the quantity of the product on the sale order line.
     *
     * @param {Event} event
     */
    setQuantity(event) {
        this.updateQuantity(parseFloat(event.target.value));
    }

    /**
     * Decrease the quantity of the product on the sale order line.
     */
    decreaseQuantity() {
        this.updateQuantity(parseFloat(this.productCatalogData.quantity - 1));
    }
}
