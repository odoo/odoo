import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { SubChannelList } from "@mail/discuss/core/public_web/sub_channel_list";
import { useChildSubEnv, useComponent } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

threadActionsRegistry.add("show-threads", {
    condition: (component) => component.thread?.hasSubThreadFeature,
    icon: "fa fa-fw fa-lg fa-comments-o",
    name: _t("Show threads"),
    component: SubChannelList,
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
    open: (component, action) =>
        action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), {
            thread: component.thread,
        }),
    sequence: (component) => (component.props.chatWindow ? 16 : 2),
    toggle: true,
});
