import { KanbanController } from "@web/views/kanban/kanban_controller";
import { onWillStart } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class ProductCatalogKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.barcodeService = useService("barcode");
        this.notification = useService("notification");
        useBus(this.barcodeService.bus, "barcode_scanned", (ev) => this.onBarcodeScannedHandler(ev.detail.barcode));
        this.orderId = this.props.context.order_id;
        this.orderResModel = this.props.context.product_catalog_order_model;
        this.backToQuotationDebounced = useDebounced(this.backToQuotation.bind(this), 500)

        onWillStart(() => this.onWillStart());
    }

    async onBarcodeScannedHandler(barcode) {
        const [product] = await this.orm.searchRead(
            "product.product",
            [["barcode", "=", barcode]],
            ["id"],
            { limit: 1 }
        );
        if (!product) {
            this.notification.add("Barcode not found!", {
                title: `product with barcode ${barcode} doesn't exist`,
                type: "danger",
                sticky: false,
            });
            return
        }
        const record = this.model.root.records.find(
            (r) => r.data.id === product.id
        );
        if (record) {
            record.productCatalogData.quantity += 1
            const ctx = record.evalContext.context
            console.log(this.model.root.context)
            const orderModel = ctx.product_catalog_order_model;
            const orderId = ctx.product_catalog_order_id;
            await rpc("/product/catalog/update_order_line_info", {
                res_model: ctx.product_catalog_order_model,
                order_id: ctx.product_catalog_order_id,
                product_id: record.data.id,
                quantity: record.productCatalogData.quantity,
                child_field: ctx.child_field,
                uom_id: record.productCatalogData.uomId || false,
            });
            return
        }
    }
    
    async onWillStart() {
        await this.setOrderStateInfo();
        this._defineButtonContent();
    }

    // Force the slot for the "Back to Quotation" button to always be shown.
    get canCreate() {
        return true;
    }

    get stateFiels() {
        return ["state"];
    }

    async setOrderStateInfo() {
        const orderData = await this.orm.searchRead(
            this.orderResModel, [["id", "=", this.orderId]], this.stateFiels
        );
        this.orderStateInfo = orderData[0] || {};
    }

    _defineButtonContent() {
        // Define the button's label depending of the order's state.
        const orderIsQuotation = ["draft", "sent"].includes(this.orderStateInfo.state);
        if (orderIsQuotation) {
            this.buttonString = _t("Back to Quotation");
        } else {
            this.buttonString = _t("Back to Order");
        }
    }

    async backToQuotation() {
        // Restore the last form view from the breadcrumbs if breadcrumbs are available.
        // If, for some weird reason, the user reloads the page then the breadcrumbs are
        // lost, and we fall back to the form view ourselves.
        if (this.env.config.breadcrumbs.length > 1) {
            await this.actionService.restore();
        } else {
            await this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: this.orderResModel,
                views: [[false, "form"]],
                view_mode: "form",
                res_id: this.orderId,
            });
        }
        this.scrollToLastLine();
    }

    scrollToLastLine() {
        const childField = this.props.context.child_field;
        const lines = document.querySelectorAll(`[name="${childField}"] [data-id]`);
        lines[lines.length - 1]?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
}
