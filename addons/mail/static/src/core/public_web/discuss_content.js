import { Component, computed, proxy, signal, types, useOnChange, useProps } from "@odoo/owl";

import { useThreadActions } from "@mail/core/common/thread_actions";
import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { ActionList } from "@mail/core/common/action_list";
import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { Thread } from "@mail/core/common/thread";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { Composer } from "@mail/core/common/composer";
import { DiscussInvitation } from "@mail/core/public_web/discuss_invitation";
import { attClassObjectToString } from "@mail/utils/common/format";

import { FileUploader } from "@web/views/fields/file_handler";
import { useService } from "@web/core/utils/hooks";

export class DiscussContent extends Component {
    static components = {
        ActionList,
        AutoresizeInput,
        DiscussAvatar,
        Thread,
        ThreadIcon,
        Composer,
        FileUploader,
        DiscussInvitation,
    };
    static template = "mail.DiscussContent";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            thread: types.instanceOf(this.store["mail.thread"]).optional(),
        });
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.rootRef = signal.ref(HTMLDivElement);
        this.threadAvatarRef = signal.ref(HTMLDivElement);
        this.threadActions = useThreadActions({ rootRef: this.rootRef, thread: () => this.thread });
        this.headerActionsList = computed(() => {
            const partition = this.threadActions.partition;
            return [partition.quick, partition.other, ...partition.group.slice().reverse()];
        });
        this.state = proxy({ jumpThreadPresent: 0 });
        this.isDiscussContent = true;
        this.attClassObjectToString = attClassObjectToString;
        this.selfGuestName = computed(() => this.store.self_guest?.name);
        this.threadDisplayName = computed(() => this.thread?.displayName);
        this.threadDescription = computed(() => this.thread?.description);
        this.onClickConfirmInvitation = this.onClickConfirmInvitation.bind(this);
        this.onClickDismissInvitation = this.onClickDismissInvitation.bind(this);
        useOnChange(
            () => [this.thread],
            () => this.actionPanelAutoOpenFn()
        );
        this.correspondentLocalDateTimeFormatted = computed(() =>
            this.store.localTimeIn(this.thread?.channel?.correspondent?.persona?.tz)
        );
    }

    actionPanelAutoOpenFn() {
        const memberListAction = this.threadActions.actions.find((a) => a.id === "member-list");
        if (memberListAction && this.store.discuss.isMemberPanelOpenByDefault) {
            memberListAction.actionPanelOpen();
        }
    }

    get thread() {
        return this.props.thread || this.store.discuss.thread;
    }

    get isNotificationTabActive() {
        return Boolean(
            this.store.messagingMenu.notificationTab?.eq(this.store.discuss.sidebarState.activeTab)
        );
    }

    get showsChatLocalDateTime() {
        return (
            this.thread.channel?.channel_type === "chat" &&
            this.correspondentLocalDateTimeFormatted()
        );
    }

    get showThreadAvatar() {
        return (
            ["channel", "group"].includes(this.thread.channel?.channel_type) ||
            this.thread.channel?.hasCorrespondentAvatar
        );
    }

    get isThreadAvatarEditable() {
        return (
            !this.thread.channel?.parent_channel_id &&
            this.thread.is_editable &&
            ["channel", "group"].includes(this.thread.channel?.channel_type)
        );
    }

    get threadDescriptionAttClass() {
        return {
            "o-mail-DiscussContent-threadDescription flex-shrink-1 small pt-1": true,
        };
    }

    get threadAvatarAttClass() {
        return {};
    }

    async onFileUploaded(file) {
        await this.thread.channel?.notifyAvatarToServer(file.data);
    }

    async renameGuest(name) {
        const newName = name.trim();
        if (this.store.self_guest.name !== newName) {
            await this.store.self_guest.updateGuestName(newName);
        }
    }

    async renameThread(name) {
        await this.thread.channel.rename(name);
    }

    async updateThreadDescription(description) {
        const newDescription = description.trim();
        if (!newDescription && !this.thread.channel.description) {
            return;
        }
        if (newDescription !== this.thread.channel.description) {
            await this.thread.channel.notifyDescriptionToServer(newDescription);
        }
    }

    get isInvitationPending() {
        return (
            !this.store.is_welcome_page_displayed &&
            this.store.channel_invitation_pending &&
            (!this.thread?.channel || this.store.channel_invitation_pending.eq(this.thread.channel))
        );
    }

    async onClickConfirmInvitation() {
        const channel = this.store.channel_invitation_pending;
        if (!channel) {
            return;
        }
        if (!channel.self_member_id) {
            await this.store.fetchStoreData("/discuss/channel/add_members", {
                channel_id: channel.id,
                user_ids: [this.store.self_user.id],
                invitation_token: channel.uuid,
            });
        }
        this.store.channel_invitation_pending = undefined;
        // refresh the channel to get the updated rtc_session_ids
        await this.store.rtc.constructor.pingChannel(channel);
        const thread = await this.store["mail.thread"].getOrFetch({
            model: "discuss.channel",
            id: channel.id,
        });
        if (thread) {
            thread.setAsDiscussThread(false);
        }
        if (channel.hasRtcSessionActive) {
            await this.store.rtc.toggleCall(channel);
        }
    }
    onClickDismissInvitation() {
        this.store.channel_invitation_pending = undefined;
    }
}
