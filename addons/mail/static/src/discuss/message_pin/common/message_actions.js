import { _t } from "@web/core/l10n/translation";
import { registerMessageAction } from "@mail/core/common/message_actions";

registerMessageAction("pin", {
    condition: (component) =>
        component.store.self_partner && component.props.thread?.model === "discuss.channel",
    icon: "fa fa-thumb-tack",
    iconLarge: "fa fa-lg fa-thumb-tack",
    name: (component) => (component.props.message.pinned_at ? _t("Unpin") : _t("Pin")),
    onSelected: (component) => component.props.message.pin(),
    sequence: 65,
});
