import {
    Component,
    computed,
    proxy,
    shallowEqual,
    signal,
    types,
    useOnChange,
    useProps,
} from "@odoo/owl";

import { useThreadActions } from "@mail/core/common/thread_actions";
import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { ActionList } from "@mail/core/common/action_list";
import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { Thread } from "@mail/core/common/thread";
import { Composer } from "@mail/core/common/composer";
import { attClassObjectToString } from "@mail/utils/common/format";

import { FileUploader } from "@web/views/fields/file_handler";
import { useService } from "@web/core/utils/hooks";
import { propSignal } from "@mail/utils/common/hooks";

export class DiscussContent extends Component {
    static components = {
        ActionList,
        AutoresizeInput,
        DiscussAvatar,
        Thread,
        Composer,
        FileUploader,
    };
    static template = "mail.DiscussContent";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        // `this.props` is read by thread actions (e.g. `owner.props.chatWindow`).
        this.props = useProps({});
        this.channel = propSignal("channel", types.instanceOf(this.store["discuss.channel"]), {
            optional: true,
        });
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.rootRef = signal.ref(HTMLDivElement);
        this.threadAvatarRef = signal.ref(HTMLDivElement);
        this.threadActions = useThreadActions({ rootRef: this.rootRef, thread: () => this.thread });
        this.headerActionsList = computed(
            () => {
                const partition = this.threadActions.partition;
                return [partition.quick, partition.other, ...partition.group.slice().reverse()];
            },
            { equals: shallowEqual }
        );
        this.state = proxy({ jumpThreadPresent: 0 });
        this.isDiscussContent = true;
        this.attClassObjectToString = attClassObjectToString;
        this.selfGuestName = computed(() => this.store.self_guest?.name);
        this.threadDisplayName = computed(() => this.thread?.displayName);
        this.threadDescription = computed(() => this.thread?.description);
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

    /** @type {import("@mail/core/common/action_list").GetActionComponent} */
    getActionComponent() {}

    get thread() {
        return this.channel?.()?.thread || this.store.discuss.thread;
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

    /** Compact header layout when a subtitle is shown (local time, meeting, out-of-office, …). */
    get hasHeaderSubline() {
        return this.showsChatLocalDateTime;
    }

    get threadNameAttClass() {
        return {
            "o-mail-DiscussContent-threadNameBox fw-bold flex-shrink-0 py-0": true,
            "fs-5": this.hasHeaderSubline,
            "fs-4": !this.hasHeaderSubline,
        };
    }

    get isThreadAvatarEditable() {
        return (
            !this.thread.channel?.parent_channel_id &&
            this.thread.is_editable &&
            ["channel", "group"].includes(this.thread.channel?.channel_type)
        );
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
}
