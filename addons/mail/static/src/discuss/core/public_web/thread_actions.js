import { useChildSubEnv } from "@web/owl2/utils";
import { registerThreadAction } from "@mail/core/common/thread_actions";
import { SubChannelList } from "@mail/discuss/core/public_web/sub_channel_list";
import { attClassObjectToString } from "@mail/utils/common/format";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

registerThreadAction("show-threads", {
    actionPanelComponent: SubChannelList,
    actionPanelComponentProps: ({ channel }) => ({ channel: channel.parent_channel_id || channel }),
    actionPanelOpen({ rootRef }) {
        this.popover?.open(
            rootRef().querySelector(`[name="${this.id}"]`),
            this.actionPanelComponentProps
        );
    },
    actionPanelOuterClass: ({ owner, store }) =>
        attClassObjectToString({
            "o-mail-SubChannelList-panel": true,
            [store.discussDropdownMenuClass(owner)]: !owner.env.inMeetingView,
        }),
    condition: ({ channel, isDiscussSidebarChannelActions }) =>
        (channel?.hasSubChannelFeature || channel?.parent_channel_id?.hasSubChannelFeature) &&
        !isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-comments-o",
    name: _t("Threads"),
    setup({ inDiscussApp, store }) {
        if (inDiscussApp && !store.env.isSmall) {
            this.popover = usePopover(SubChannelList, {
                onClose: () => this.actionPanelClose(),
                fixedPosition: true,
                popoverClass: this.actionPanelOuterClass,
            });
        }
        useChildSubEnv({ subChannelMenu: { open: () => this.actionPanelOpen() } });
    },
    sequence: ({ chatWindow }) => (chatWindow ? 40 : 5),
    sequenceGroup: 10,
});
