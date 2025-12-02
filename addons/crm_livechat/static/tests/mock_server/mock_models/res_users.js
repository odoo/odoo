import { mailModels } from "@mail/../tests/mail_test_helpers";
import { serverState } from "@web/../tests/web_test_helpers";

export class ResUsers extends mailModels.ResUsers {
    /** @override */
    _init_store_data(store) {
        super._init_store_data(...arguments);
        store.add({
            has_access_create_lead: this.env.user?.group_ids.includes(serverState.groupSalesTeamId),
        });
    }
}
