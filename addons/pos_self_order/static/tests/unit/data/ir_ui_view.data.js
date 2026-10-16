import { patch } from "@web/core/utils/patch";
import { IrUiView } from "@point_of_sale/../tests/unit/data/ir_ui_view.data";
import { loadQwebTemplates } from "@point_of_sale/../tests/unit/utils";

let receiptTemplatesPromise;

patch(IrUiView.prototype, {
    async _load_pos_self_data_read(records) {
        receiptTemplatesPromise ||= loadQwebTemplates(this._get_xml_ids_to_load());
        return [...records, ...(await receiptTemplatesPromise)];
    },
});
