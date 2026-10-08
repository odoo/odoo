import { unmockedOrm } from "@web/../tests/_framework/module_set.hoot";
import { patch } from "@web/core/utils/patch";
import { IrUiView } from "@point_of_sale/../tests/unit/data/ir_ui_view.data";

let receiptTemplatesPromise;

export async function loadQwebTemplates(xmlIds) {
    const views = await unmockedOrm(
        "ir.ui.view",
        "search_read",
        [[["key", "in", xmlIds]], ["key"]],
        {}
    );
    const idByKey = Object.fromEntries(views.map(({ id, key }) => [key, id]));
    return Promise.all(
        xmlIds.map(async (key) => ({
            key,
            _template: await unmockedOrm("ir.ui.view", "get_combined_arch", [[idByKey[key]]], {}),
        }))
    );
}

patch(IrUiView.prototype, {
    async _load_pos_self_data_read(records) {
        receiptTemplatesPromise ||= loadQwebTemplates(this._get_xml_ids_to_load());
        return [...records, ...(await receiptTemplatesPromise)];
    },
});
