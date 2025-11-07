import { serverState } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";

export class ResGroups extends mailModels.ResGroups {
    _records = [
        ...this._records,
        {
            id: serverState.groupLivechatId,
            name: "Livechat User",
            privilege_id: false,
        },
        {
            id: serverState.groupLivechatManagerId,
            name: "Livechat Manager",
            privilege_id: false,
        },
    ];
}
