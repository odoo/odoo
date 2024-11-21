import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { SubChannelList } from "@mail/discuss/core/public_web/sub_channel_list";
import { useChildSubEnv, useComponent } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

threadActionsRegistry.add("show-threads", {
    close(component, action) {
        action.popover?.close();
    },
    condition: (component) =>
        component.thread?.hasSubChannelFeature ||
        component.thread?.parent_channel_id?.hasSubChannelFeature,
    icon: "fa fa-fw fa-comments-o",
    iconLarge: "fa fa-fw fa-lg fa-comments-o",
    name: _t("Threads"),
    component: SubChannelList,
    componentProps(action) {
        return { close: () => action.close() };
    },
    setup(action) {
        const component = useComponent();
        if (!component.props.chatWindow) {
            action.popover = usePopover(SubChannelList, {
                onClose: () => action.close(),
                fixedPosition: true,
            });
        }
        useChildSubEnv({
            subChannelMenu: {
                open: () => action.open(),
            },
        });
    },
    open: (component, action) => {
        const thread = component.thread?.parent_channel_id || component.thread;
        action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), { thread });
    },
    sequence: (comp) => (comp.props.chatWindow ? 40 : 5),
    sequenceGroup: 10,
    toggle: true,
});
