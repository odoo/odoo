import { session } from "@web/session";
import { barcodeReaderService } from "@point_of_sale/app/services/barcode_reader_service";
import { patch } from "@web/core/utils/patch";
import { usePlugin } from "@odoo/owl";
import { PosDataPlugin } from "@point_of_sale/app/plugins/pos_data_plugin";

patch(barcodeReaderService, {
    async start(env, deps) {
        this.data = usePlugin(PosDataPlugin);
        session.nomenclature_id = this.data.models["barcode.nomenclature"].getFirst();
        session.nomenclature_id.rules = session.nomenclature_id.rule_ids; //TODO change rules to rule_ids everywhere
        return super.start(env, deps);
    },
});
