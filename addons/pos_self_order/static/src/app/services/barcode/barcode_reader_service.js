import { session } from "@web/session";
import { barcodeReaderService } from "@point_of_sale/app/services/barcode_reader_service";
import { patch } from "@web/core/utils/patch";
import { usePlugin } from "@odoo/owl";
import { PosDataPlugin } from "@point_of_sale/app/plugins/pos_data_plugin";

patch(barcodeReaderService, {
    async start(env, deps) {
        const data = usePlugin(PosDataPlugin);
        // No nomenclature (the company field is optional): leave session.nomenclature_id unset,
        // the base service then creates no reader and useBarcodeReader registers nothing
        const nomenclature = data.models["barcode.nomenclature"]?.getFirst();
        if (nomenclature) {
            session.nomenclature_id = nomenclature;
            nomenclature.rules = nomenclature.rule_ids;
        }
        return super.start(env, deps);
    },
});
