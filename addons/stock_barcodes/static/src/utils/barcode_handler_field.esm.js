/** @odoo-module **/
import {BarcodeHandlerField} from "@barcodes/barcode_handler_field";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
const {useEffect} = owl;

patch(BarcodeHandlerField.prototype, "stock_barcodes.BarcodeHandlerField", {
    /* eslint-disable no-unused-vars */
    setup() {
        this._super(...arguments);
        const busService = useService("bus_service");
        this.orm = useService("orm");
        const notifyChanges = async ({detail: notifications}) => {
            for (const {payload, type} of notifications) {
                if (type === "stock_barcodes_refresh_data") {
                    await this.env.model.root.load();
                    this.env.model.notify();
                }
            }
        };
        useEffect(() => {
            busService.addChannel("barcode_reload");
            busService.addEventListener("notification", notifyChanges);
            return () => {
                busService.deleteChannel("barcode_reload");
                busService.removeEventListener("notification", notifyChanges);
            };
        });
    },
    onBarcodeScanned(event) {
        this._super(...arguments);
        if (this.props.record.resModel.includes("wiz.stock.barcodes.read")) {
            $("#dummy_on_barcode_scanned").click();
        }
    },
});
