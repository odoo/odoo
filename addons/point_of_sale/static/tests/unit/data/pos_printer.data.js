import { models } from "@web/../tests/web_test_helpers";

export class PosPrinter extends models.ServerModel {
    _name = "pos.printer";

    _load_pos_data_fields() {
        return ["id", "name", "proxy_ip", "product_categories_ids", "printer_type"];
    }
}
