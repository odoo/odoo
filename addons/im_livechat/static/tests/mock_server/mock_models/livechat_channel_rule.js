import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";
import { models } from "@web/../tests/web_test_helpers";

export class LivechatChannelRule extends models.ServerModel {
    _name = "im_livechat.channel.rule";

    get _to_store_defaults() {
        return ["action", "auto_popup_timer", mailDataHelpers.Store.one("chatbot_script_id")];
    }

    match_rule(channel_id) {
        const [rule] = this._filter([["channel_id", "=", channel_id]]);
        return this.browse(rule ? [rule.id] : []);
    }
}
