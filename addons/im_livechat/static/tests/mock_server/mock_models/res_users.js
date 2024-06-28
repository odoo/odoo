import { mailModels } from "@mail/../tests/mail_test_helpers";
import { serverState } from "@web/../tests/web_test_helpers";

export class ResUsers extends mailModels.ResUsers {
    /**
     * @override
     */
    _init_store_data(store) {
        super._init_store_data(...arguments);
        store.add({
            has_access_livechat: this.env.user?.groups_id.includes(serverState.groupLivechatId),
        });
    }
}
