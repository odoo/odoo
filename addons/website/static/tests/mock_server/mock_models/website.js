import { models } from "@web/../tests/web_test_helpers";

export class Website extends models.ServerModel {
    _name = "website";

    _store_website_fields(res) {
        res.attr("name");
    }

    // get_module_toggle_info() {
    //     return false;
    // }
}
