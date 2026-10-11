import { models } from "@web/../tests/web_test_helpers";
import { unmockedOrm } from "@web/../tests/_framework/module_set.hoot";

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

export class IrUiView extends models.ServerModel {
    _name = "ir.ui.view";

    _load_pos_data_fields() {
        return ["id", "key"];
    }

    // Modules overriding the Python `_get_xml_ids_to_load` (e.g. l10n_tw_edi_ecpay_pos,
    // pos_iot_six) to add their own receipt xmlids should `patch()` this method the same
    // way, appending to `super()`'s list, so their own hoot tests can render those receipts.
    _get_xml_ids_to_load() {
        return [
            "point_of_sale.pos_order_receipt_header",
            "point_of_sale.pos_order_receipt_style",
            "point_of_sale.company_info_receipt",
            "point_of_sale.pos_orderline_receipt_information",
            "point_of_sale.pos_orderline_receipt",
            "point_of_sale.pos_order_receipt_footer",
            "point_of_sale.pos_order_receipt",
            "point_of_sale.pos_order_change_receipt",
            "point_of_sale.pos_order_change_receipt_zpl",
            "point_of_sale.pos_order_change_receipt_line",
            "point_of_sale.pos_cash_move_receipt",
            "point_of_sale.pos_tip_receipt",
            "point_of_sale.pos_sale_details_receipt",
            "point_of_sale.pos_sale_details_receipt_product_line",
        ];
    }

    async _load_pos_data_read(records) {
        receiptTemplatesPromise ||= loadQwebTemplates(this._get_xml_ids_to_load());
        return [...records, ...(await receiptTemplatesPromise)];
    }
}
