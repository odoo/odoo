import { patch } from "@web/core/utils/patch";
import { useService, useBus } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";

patch(ProductCatalogKanbanController.prototype, {
    setup() {
        super.setup();
        this.barcodeService = useService("barcode");
        this.notification = useService("notification");
        useBus(this.barcodeService.bus, "barcode_scanned", (ev) => this.onBarcodeScannedHandler(ev.detail.barcode));
    },

    async onBarcodeScannedHandler(barcode) {
        const searchModel = this.env.model.env.searchModel
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
        const barcode_and_order_domain = `['|', ("barcode", "=", "${barcode}"), ('catalog_is_in_order', '=', "True")]`
        const filter = searchModel.getSearchItems().find((item) => item.description == "Items in order")
        if (!filter) {
            searchModel.createNewFilters([{
            description: 'Items in order',
            domain: barcode_and_order_domain,
            }])
        } else {
            filter.domain = barcode_and_order_domain
            if (!filter.isActive) {
                searchModel.toggleSearchItem(filter.id)
            }
        }
        
        const product_id = product.id
        const res_model = this.props.context.product_catalog_order_model
        const order_id = this.props.context.order_id
        const child_field = this.props.context.child_field

        const orderLinesInfo = await rpc("/product/catalog/order_lines_info",{
            res_model: res_model,
            order_id: order_id,
            product_ids: [product_id],
            child_field: child_field
        });
        const newQuantity = (orderLinesInfo[product_id]?.quantity || 0) + 1;
        await rpc("/product/catalog/update_order_line_info", {
            res_model: res_model,
            order_id: order_id,
            product_id: product_id,
            quantity: newQuantity,
            child_field: child_field,
            uom_id: orderLinesInfo[product_id].uomId,
        });

        await searchModel._notify();

        return
    },
});
