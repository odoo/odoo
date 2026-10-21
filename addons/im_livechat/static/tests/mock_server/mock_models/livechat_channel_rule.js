import { models } from "@web/../tests/web_test_helpers";

export class LivechatChannelRule extends models.ServerModel {
    _name = "im_livechat.channel.rule";

    _store_channel_rule_fields(res) {
        res.extend(["action", "auto_popup_timer"]);
        res.one("chatbot_script_id", "_store_script_fields");
    }

    match_rule(channel_id) {
        const [rule] = this._filter([["channel_id", "=", channel_id]]);
        return this.browse(rule ? [rule.id] : []);
    }
}
