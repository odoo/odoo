import { livechatModels } from "@im_livechat/../tests/livechat_test_helpers";

export class ResUsers extends livechatModels.ResUsers {
    /** @override */
    _init_store_data(store) {
        super._init_store_data(...arguments);
        store.add_global_values({
            has_multi_website: this.has_group("website.group_multi_website"),
        });
    }
}
