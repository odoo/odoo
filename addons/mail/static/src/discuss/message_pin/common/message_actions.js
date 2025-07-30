import { _t } from "@web/core/l10n/translation";
import { messageActionsRegistry } from "@mail/core/common/message_actions";

messageActionsRegistry.add("pin", {
    condition: (component) =>
        component.store.self.type === "partner" &&
        component.props.thread?.model === "discuss.channel",
    icon: "fa fa-thumb-tack",
    /** @deprecated use `name` instead */
    title: (comp, action) => action.name,
    name: (component) => (component.props.message.pinned_at ? _t("Unpin") : _t("Pin")),
    /** @deprecated use `onSelected` instead */
    onClick: (component, action, ...args) => action.onSelected(component, action, ...args),
    onSelected: (component) => component.props.message.pin(),
    sequence: 65,
});
