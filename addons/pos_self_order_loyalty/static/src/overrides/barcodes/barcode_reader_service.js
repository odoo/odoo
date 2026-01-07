import { session } from "@web/session";
import { barcodeReaderService } from "@point_of_sale/app/services/barcode_reader_service";
import { patch } from "@web/core/utils/patch";

barcodeReaderService.dependencies = [...barcodeReaderService.dependencies, "pos_data"];


patch(barcodeReaderService, {
    async start(env, deps) {
        const { pos_data } = deps;
        session.nomenclature_id = pos_data.models['barcode.nomenclature'].getFirst();
        session.nomenclature_id.rules = session.nomenclature_id.rule_ids; //TODO change rules to rule_ids everywhere
        return super.start(env, deps);
    }
})
