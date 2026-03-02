import { useLayoutEffect, useRef, useState } from "@web/owl2/utils";
import { Component } from "@odoo/owl";

import { useThreadActions } from "@mail/core/common/thread_actions";
import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { ActionList } from "@mail/core/common/action_list";
import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { Thread } from "@mail/core/common/thread";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { Composer } from "@mail/core/common/composer";
import { useDynamicInterval } from "@mail/utils/common/misc";
import { formatLocalDateTime } from "@mail/utils/common/dates";
import { attClassObjectToString } from "@mail/utils/common/format";

import { FileUploader } from "@web/views/fields/file_handler";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

export class DiscussContent extends Component {
    static components = {
        ActionList,
        AutoresizeInput,
        DiscussAvatar,
        Thread,
        ThreadIcon,
        Composer,
        FileUploader,
        Dropdown,
        DropdownItem,
    };
    static props = ["thread?"];
    static template = "mail.DiscussContent";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.threadActions = useThreadActions({ thread: () => this.thread });
        this.root = useRef("root");
        this.state = useState({ jumpThreadPresent: 0 });
        this.isDiscussContent = true;
        this.attClassObjectToString = attClassObjectToString;
        useLayoutEffect(
            () => this.actionPanelAutoOpenFn(),
            () => [this.thread]
        );
        useDynamicInterval(
            (partnerTz, currentUserTz) => {
                this.state.correspondentLocalDateTimeFormatted = formatLocalDateTime(
                    partnerTz,
                    currentUserTz
                );
                if (!this.state.correspondentLocalDateTimeFormatted) {
                    return;
                }
                return 60000 - (Date.now() % 60000);
            },
            () => [this.thread?.correspondent?.persona?.tz, this.store.self?.tz]
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

    get showsChatLocalDateTime() {
        return (
            this.thread.channel?.channel_type === "chat" &&
            this.state.correspondentLocalDateTimeFormatted
        );
    }

    get showThreadAvatar() {
        return ["channel", "group", "chat"].includes(this.thread.channel?.channel_type);
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

    get threadName() {
        if (this.thread.model === "mail.box") {
            return this.store.self_user?.notification_type === "inbox"
                ? _t("Inbox")
                : _t("Bookmarks");
        }
        return this.thread.displayName || "";
    }

    onMailboxSelected(mailbox) {
        mailbox.setAsDiscussThread();
        this.refetch(mailbox);
    }

    onMailboxFilterSelected(filter) {
        this.store.activeMailboxFilter =
            this.store.activeMailboxFilter === filter ? undefined : filter;
        this.refetch(this.store.discuss.thread);
    }

    async refetch(thread) {
        Object.assign(thread, {
            status: "new",
            isLoaded: false,
            loadOlder: false,
            loadNewer: false,
            scrollTop: undefined,
            phantomMessage: thread.messages,
        });
        thread.messages = await thread.fetchMessages();
        thread.phantomMessages = [];
    }
}
