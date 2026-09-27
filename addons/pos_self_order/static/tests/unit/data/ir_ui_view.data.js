import { unmockedOrm } from "@web/../tests/_framework/module_set.hoot";
import { patch } from "@web/core/utils/patch";
import { IrUiView } from "@point_of_sale/../tests/unit/data/ir_ui_view.data";

let receiptTemplatesPromise;

patch(IrUiView.prototype, {
    async _load_pos_self_data_read(records) {
        if (!receiptTemplatesPromise) {
            const xmlIds = this._get_xml_ids_to_load();
            receiptTemplatesPromise = unmockedOrm(
                "ir.ui.view",
                "search_read",
                [[["key", "in", xmlIds]], ["key", "arch"]],
                {}
            );
        }
        const templates = await receiptTemplatesPromise;
        return [...records, ...templates.map(({ key, arch }) => ({ key, _template: arch }))];
    },
});
