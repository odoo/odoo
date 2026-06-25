import { models } from "@web/../tests/web_test_helpers";

export class PosProductTemplateSnooze extends models.ServerModel {
    _name = "pos.product.template.snooze";

    _load_pos_data_fields() {
        return ["id", "product_template_id", "pos_config_id", "start_time", "end_time"];
    }
}
