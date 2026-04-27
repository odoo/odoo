import { models } from "@web/../tests/web_test_helpers";

export class CRMLead extends models.ServerModel {
    _name = "crm.lead";

    /** @override */
    get_formview_id() {
        return false;
    }
}
