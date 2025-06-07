import { serverState, webModels } from "@web/../tests/web_test_helpers";

export class ResGroups extends webModels.ResGroups {
    _records = [
        ...this._records,
        {
            id: serverState.groupLivechatId,
            name: "Livechat User",
        },
    ];
}
