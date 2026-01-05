import { MessageConfirmDialog } from "@mail/core/common/message_confirm_dialog";
import { fields, Record } from "@mail/model/export";

import { _t } from "@web/core/l10n/translation";
import { Deferred } from "@web/core/utils/concurrency";
import { rpc } from "@web/core/network/rpc";
import {
    compareDatetime,
    effectWithCleanup,
    nearestGreaterThanOrEqual,
} from "@mail/utils/common/misc";
import { formatList } from "@web/core/l10n/utils";
import { imageUrl } from "@web/core/utils/urls";

/** @import { AwaitChatHubInit } from "@mail/core/common/chat_hub_model" */

export class DiscussChannel extends Record {
    static _name = "discuss.channel";
    static _inherits = { "mail.thread": "thread" };
    static id = "id";

    static new() {
        /** @type {import("models").DiscussChannel} */
        const channel = super.new(...arguments);
        // Handles subscriptions for non-members. Subscriptions for channels
        // that the user is a member of are handled by
        // `ir_websocket@_build_bus_channel_list`.
        effectWithCleanup({
            effect(busChannel, busService) {
                if (busService && busChannel) {
                    busService.addChannel(busChannel);
                    return () => busService.deleteChannel(busChannel);
                }
            },
            dependencies: (channel) => [
                !channel.isTransient &&
                    !channel.self_member_id &&
                    channel.shouldSubscribeToBusChannel &&
                    channel.busChannel,
                channel.store.env.services.bus_service,
            ],
            reactiveTargets: [channel],
        });
        return channel;
    }

    /**
     * Retrieve an existing channel from the store or fetch it if missing.
     *
     * @param {number} channel_id
     * @return {Promise<DiscussChannel>}
     */
    static getOrFetch(channel_id) {
        const channel = this.store["discuss.channel"].get(channel_id);
        if (channel?.fetchChannelInfoState === "fetched" || channel_id < 0) {
            return Promise.resolve(channel);
        }
        const fetchChannelInfoDeferred = this.store.channelIdsFetchingDeferred.get(channel_id);
        if (fetchChannelInfoDeferred) {
            return fetchChannelInfoDeferred;
        }
        const def = new Deferred();
        this.store.channelIdsFetchingDeferred.set(channel_id, def);
        this.store.fetchChannel(channel_id).then(
            () => {
                this.store.channelIdsFetchingDeferred.delete(channel_id);
                const channel = this.store["discuss.channel"].get(channel_id);
                if (channel?.exists()) {
                    channel.fetchChannelInfoState = "fetched";
                    def.resolve(channel);
                } else {
                    def.resolve();
                }
            },
            () => {
                this.store.channelIdsFetchingDeferred.delete(channel_id);
                const channel = this.store["discuss.channel"].get(channel_id);
                if (channel?.exists()) {
                    def.reject(channel);
                } else {
                    def.reject();
                }
            }
        );
        return def;
    }

    /** Equivalent to DiscussChannel._allow_invite_by_email */
    get allow_invite_by_email() {
        return (
            this.channel_type === "group" ||
            (this.channel_type === "channel" && !this.group_public_id)
        );
    }
    get allowDescriptionsTypes() {
        return ["channel", "group"];
    }
    get allowDescription() {
        return this.allowDescriptionsTypes.includes(this.channel_type);
    }
    get allowedToLeaveChannelTypes() {
        return ["channel", "group"];
    }
    get areAllMembersLoaded() {
        return this.member_count === this.channel_member_ids.length;
    }
    /** @type {string} */
    avatar_cache_key;
    get avatarUrl() {
        if (["channel", "group"].includes(this.channel_type)) {
            return imageUrl("discuss.channel", this.id, "avatar_128", {
                unique: this.avatar_cache_key,
            });
        }
        return this.correspondent?.avatarUrl;
    }
    /** @type {"video_full_screen"|undefined} */
    default_display_mode;
    get typesAllowingCalls() {
        return ["chat", "channel", "group"];
    }
    get allowCalls() {
        return (
            !this.isTransient &&
            this.typesAllowingCalls.includes(this.channel_type) &&
            !this.correspondent?.persona.eq(this.store.odoobot)
        );
    }
    canHide = fields.Attr(false, {
        compute() {
            return this._computeCanHide();
        },
    });
    _computeCanHide() {
        return Boolean(this.self_member_id?.is_pinned);
    }
    channel_member_ids = fields.Many("discuss.channel.member", {
        inverse: "channel_id",
        onDelete: (r) => r?.delete(),
        sort: (m1, m2) => m1.id - m2.id,
    });
    channel_name_member_ids = fields.Many("discuss.channel.member");
    /** @type {"chat"|"channel"|"group"|"livechat"|"whatsapp"|"ai_chat"|"ai_composer"} */
    channel_type;
    /** ⚠️ {@link AwaitChatHubInit} */
    chatWindow = fields.One("ChatWindow", {
        inverse: "channel",
        onAdd() {
            if (this.self_member_id && !this.self_member_id.is_pinned) {
                this.self_member_id.is_pinned = true;
                this.pinRpc({ pinned: true });
            }
        },
        onDelete() {
            this._onDeleteChatWindow();
        },
    });
    get chatChannelTypes() {
        return ["chat", "group"];
    }
    correspondent = fields.One("discuss.channel.member", {
        /** @this {import("models").Thread} */
        compute() {
            return this.computeCorrespondent();
        },
    });
    correspondentCountry = fields.One("res.country", {
        /** @this {import("models").Thread} */
        compute() {
            return this.correspondent?.persona?.country_id ?? this.country_id;
        },
    });
    /** @returns {import("models").ChannelMember} */
    computeCorrespondent() {
        if (this.channel_type === "channel") {
            return undefined;
        }
        const correspondents = this.correspondents;
        if (correspondents.length === 1) {
            // 2 members chat.
            return correspondents[0];
        }
        if (correspondents.length === 0 && this.channel_member_ids.length === 1) {
            // Self-chat.
            return this.channel_member_ids[0] ?? [];
        }
        return undefined;
    }
    /** @returns {import("models").ChannelMember[]} */
    get correspondents() {
        if (!this.channel) {
            return [];
        }
        return this.channel_member_ids.filter(({ persona }) => persona?.notEq(this.store.self));
    }
    get displayName() {
        if (this.supportsCustomChannelName && this.self_member_id?.custom_channel_name) {
            return this.self_member_id.custom_channel_name;
        }
        if (this.channel_type === "chat" && this.correspondent) {
            return this.correspondent.name;
        }
        if (this.channel_name_member_ids.length && !this.name) {
            const nameParts = this.channel_name_member_ids
                .sort((m1, m2) => m1.id - m2.id)
                .slice(0, 3)
                .map((member) => member.name);
            if (this.member_count > 3) {
                const remaining = this.member_count - 3;
                nameParts.push(remaining === 1 ? _t("1 other") : _t("%s others", remaining));
            }
            return formatList(nameParts);
        }
        return this.name;
    }
    /** @type {"not_fetched"|"pending"|"fetched"} */
    fetchMembersState = "not_fetched";
    /** @type {"not_fetched"|"fetching"|"fetched"} */
    fetchChannelInfoState = "not_fetched";
    from_message_id = fields.One("mail.message", { inverse: "linkedSubChannel" });
    get fullNameWithParent() {
        const text = this.parent_channel_id
            ? `${this.parent_channel_id.displayName} > ${this.displayName}`
            : this.displayName;
        return text;
    }
    get memberListTypes() {
        return ["channel", "group"];
    }
    get hasMemberList() {
        return this.memberListTypes.includes(this.channel_type);
    }
    get isHideUntilNewMessageSupported() {
        return Boolean(this.self_member_id);
    }
    last_interest_dt = fields.Datetime();
    lastInterestDt = fields.Datetime({
        /** @this {import("models").Thread} */
        compute() {
            return compareDatetime(this.self_member_id?.last_interest_dt, this.last_interest_dt) > 0
                ? this.self_member_id?.last_interest_dt
                : this.last_interest_dt;
        },
    });
    onlineMembers = fields.Many("discuss.channel.member", {
        /** @this {import("models").DiscussChannel} */
        compute() {
            return this.channel_member_ids
                .filter((member) => member.isOnline)
                .sort((m1, m2) => this.store.sortMembers(m1, m2)); // FIXME: sort are prone to infinite loop (see test "Display livechat custom name in typing status")
        },
    });
    get hasAttachmentPanel() {
        return true;
    }
    firstUnreadMessage = fields.One("mail.message", {
        /** @this {import("models").DiscussChannel} */
        compute() {
            if (!this.self_member_id) {
                return null;
            }
            const messages = this.messages.filter((m) => !m.isNotification);
            const separator = this.self_member_id.new_message_separator_ui;
            if (separator === 0 && !this.loadOlder) {
                return messages[0];
            }
            if (!separator || messages.length === 0 || messages.at(-1).id < separator) {
                return null;
            }
            // try to find a perfect match according to the member's separator
            let message = this.store["mail.message"].get({ id: separator });
            if (!message || this.notEq(message.channel_id)) {
                message = nearestGreaterThanOrEqual(messages, separator, (msg) => msg.id);
            }
            return message;
        },
    });
    hasOtherMembersTyping = fields.Attr(false, {
        /** @this {import("models").DiscussChannel} */
        compute() {
            return this.otherTypingMembers.length > 0;
        },
    });
    hasSeenFeature = fields.Attr(false, {
        /** @this {import("models").DiscussChannel} */
        compute() {
            return this.store.channel_types_with_seen_infos.includes(this.channel_type);
        },
    });
    /** @type {number} */
    id = fields.Attr(undefined, {
        onUpdate() {
            const busService = this.store.env.services.bus_service;
            if (!busService.isActive && !this.isTransient) {
                busService.start();
            }
        },
    });
    get invitationLink() {
        if (!this.uuid || this.channel_type === "chat") {
            return undefined;
        }
        return `${window.location.origin}/chat/${this.id}/${this.uuid}`;
    }
    invited_member_ids = fields.Many("discuss.channel.member");
    lastMessageSeenByAllId = fields.Attr(undefined, {
        /** @this {import("models").DiscussChannel} */
        compute() {
            if (!this.hasSeenFeature) {
                return;
            }
            return this.channel_member_ids.reduce((lastMessageSeenByAllId, member) => {
                if (member.notEq(this.self_member_id) && member.seen_message_id) {
                    return lastMessageSeenByAllId
                        ? Math.min(lastMessageSeenByAllId, member.seen_message_id.id)
                        : member.seen_message_id.id;
                } else {
                    return lastMessageSeenByAllId;
                }
            }, undefined);
        },
    });
    lastSelfMessageSeenByEveryone = fields.One("mail.message", {
        /** @this {import("models").DiscussChannel} */
        compute() {
            if (!this.lastMessageSeenByAllId) {
                return false;
            }
            let res;
            // starts from most recent persistent messages to find early
            for (let i = this.persistentMessages.length - 1; i >= 0; i--) {
                const message = this.persistentMessages[i];
                if (!message.isSelfAuthored) {
                    continue;
                }
                if (message.id > this.lastMessageSeenByAllId) {
                    continue;
                }
                res = message;
                break;
            }
            return res;
        },
    });
    /**
     * To be overridden.
     * The purpose is to exclude technical channel_member_ids like bots and avoid
     * "wrong" seen message indicator
     * @returns {import("models").ChannelMember[]}
     */
    get membersThatCanSeen() {
        return this.channel_member_ids;
    }
    /** @type {Number|undefined} */
    member_count;
    /** @type {string} */
    name;
    /** ⚠️ {@link AwaitChatHubInit} */
    get shouldSubscribeToBusChannel() {
        return this.chatWindow?.isOpen;
    }
    get isChatChannel() {
        return this.chatChannelTypes.includes(this.channel_type);
    }
    otherTypingMembers = fields.Many("discuss.channel.member", {
        /** @this {import("models").DiscussChannel} */
        compute() {
            return this.typingMembers.filter((member) => !member.persona?.eq(this.store.self));
        },
    });
    offlineMembers = fields.Many("discuss.channel.member", {
        /** @this {import("models").DiscussChannel} */
        compute() {
            return this._computeOfflineMembers().sort(
                (m1, m2) => this.store.sortMembers(m1, m2) // FIXME: sort are prone to infinite loop (see test "Display livechat custom name in typing status")
            );
        },
    });
    /** @type {true|undefined} */
    open_chat_window = fields.Attr(undefined, {
        /** @this {import("models").Thread} */
        onUpdate() {
            if (this.open_chat_window) {
                this.open_chat_window = undefined;
                this.openChatWindow({ focus: true });
            }
        },
    });
    parent_channel_id = fields.One("discuss.channel", {
        inverse: "sub_channel_ids",
        onDelete() {
            this.delete();
        },
    });
    /** @type {"loaded"|"loading"|"error"|undefined} */
    pinnedMessagesState = undefined;
    get showCorrespondentCountry() {
        return false;
    }
    get showImStatus() {
        return (
            (this.channel_type === "chat" && this.correspondent) ||
            (this.channel_type === "group" && this.hasOtherMembersTyping)
        );
    }
    get showUnreadBanner() {
        return this.self_member_id?.message_unread_counter_ui > 0;
    }
    sub_channel_ids = fields.Many("discuss.channel", {
        inverse: "parent_channel_id",
        sort: (a, b) => compareDatetime(b.lastInterestDt, a.lastInterestDt) || b.id - a.id,
    });
    self_member_id = fields.One("discuss.channel.member", {
        inverse: "channelAsSelf",
        onDelete() {
            this.onPinStateUpdated();
        },
    });
    thread = fields.One("mail.thread", {
        compute() {
            return { id: this.id, model: "discuss.channel" };
        },
        inverse: "channel",
        onDelete: (r) => r?.delete(),
    });
    memberBusSubscription = fields.Attr(false, {
        /** @this {import("models").Thread} */
        compute() {
            return (
                this.self_member_id?.memberSince >= this.store.env.services.bus_service.startedAt
            );
        },
        onUpdate() {
            this.store.updateBusSubscription();
        },
    });
    typingMembers = fields.Many("discuss.channel.member", { inverse: "channelAsTyping" });
    get unknownMembersCount() {
        return (this.member_count ?? 0) - (this.channel_member_ids.length ?? 0);
    }

    _onDeleteChatWindow() {}

    delete() {
        this.chatWindow?.close();
        super.delete(...arguments);
    }

    async fetchChannelMembers() {
        if (this.fetchMembersState === "pending") {
            return;
        }
        const previousState = this.fetchMembersState;
        this.fetchMembersState = "pending";
        const known_member_ids = this.channel_member_ids.map((channelMember) => channelMember.id);
        let data;
        try {
            data = await rpc("/discuss/channel/members", {
                channel_id: this.id,
                known_member_ids: known_member_ids,
            });
        } catch (e) {
            this.fetchMembersState = previousState;
            throw e;
        }
        this.fetchMembersState = "fetched";
        this.store.insert(data);
    }

    async fetchPinnedMessages() {
        if (["loaded", "loading"].includes(this.pinnedMessagesState)) {
            return;
        }
        this.pinnedMessagesState = "loading";
        try {
            await this.thread.fetchPinnedMessages();
        } catch (e) {
            this.pinnedMessagesState = "error";
            throw e;
        }
        this.pinnedMessagesState = "loaded";
    }

    async fetchMoreAttachments(limit = 30) {
        if (this.isLoadingAttachments || this.areAttachmentsLoaded) {
            return;
        }
        this.isLoadingAttachments = true;
        try {
            const data = await rpc("/discuss/channel/attachments", {
                before: Math.min(...this.attachments.map(({ id }) => id)),
                channel_id: this.id,
                limit,
            });
            this.store.insert(data.store_data);
            if (data.count < limit) {
                this.areAttachmentsLoaded = true;
            }
        } finally {
            this.isLoadingAttachments = false;
        }
    }

    async leaveChannel() {
        if (this.channel_type === "channel" && this.create_uid?.eq(this.store.self_user)) {
            await this.askLeaveConfirmation(
                _t("You are the administrator of this channel. Are you sure you want to leave?")
            );
        }
        if (this.channel_type === "group") {
            await this.askLeaveConfirmation(
                _t(
                    "You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?"
                )
            );
        }
        await this.leaveChannelProcess();
    }

    async leaveChannelProcess() {
        await this.closeChatWindow();
        if (this.exists()) {
            await this.leaveChannelRpc();
        }
    }

    async leaveChannelRpc() {
        await this.store.env.services.orm.silent.call("discuss.channel", "action_unfollow", [
            this.id,
        ]);
    }

    async markAsFetched() {
        await this.store.env.services.orm.silent.call("discuss.channel", "channel_fetched", [
            [this.id],
        ]);
    }

    messagePin(message) {
        this.store.env.services.dialog.add(MessageConfirmDialog, {
            confirmText: _t("Yeah, pin it!"),
            message,
            prompt: _t("You sure want this message pinned to %(conversation)s forever and ever?", {
                conversation: this.prefix + this.displayName,
            }),
            size: "md",
            title: _t("Pin It"),
            onConfirm: () => {
                this.setMessagePin(message, true);
            },
        });
    }

    messageUnpin(message) {
        this.store.env.services.dialog.add(MessageConfirmDialog, {
            confirmColor: "btn-danger",
            confirmText: _t("Yes, remove it please"),
            message,
            prompt: _t(
                "Well, nothing lasts forever, but are you sure you want to unpin this message?"
            ),
            size: "md",
            title: _t("Unpin Message"),
            onConfirm: () => {
                this.setMessagePin(message, false);
            },
        });
    }

    /** @param {string} data base64 representation of the binary */
    async notifyAvatarToServer(data) {
        await rpc("/discuss/channel/update_avatar", { channel_id: this.id, data });
    }

    onPinStateUpdated() {}

    /** @returns {boolean} true if the channel was opened, false otherwise */
    openChannel() {
        if (this.self_member_id && !this.self_member_id.is_pinned) {
            this.self_member_id.is_pinned = true;
            this.pinRpc({ pinned: true });
        }
        return this._openChannel();
    }

    _openChannel() {
        return false;
    }

    pinRpc({ pinned = true } = {}) {
        return this.store.fetchStoreData(
            "/discuss/channel/pin",
            { channel_id: this.id, pinned },
            { readonly: false }
        );
    }

    /** @param {string} name */
    async rename(name) {
        const newName = name.trim();
        if (
            newName !== this.displayName &&
            ((newName && this.channel?.channel_type === "channel") || this.channel?.isChatChannel)
        ) {
            if (["channel", "group"].includes(this.channel_type)) {
                this.name = newName;
                await this.store.env.services.orm.call(
                    "discuss.channel",
                    "channel_rename",
                    [[this.id]],
                    { name: newName }
                );
            } else if (this.supportsCustomChannelName) {
                if (this.self_member_id) {
                    this.self_member_id.custom_channel_name = newName;
                }
                await this.store.env.services.orm.call(
                    "discuss.channel",
                    "channel_set_custom_name",
                    [[this.id]],
                    { name: newName }
                );
            }
        }
    }

    /**
     * @param {Object} param0
     * @param {boolean} [param0.notify=true]
     * @param {Map<import("models").DiscussChannel, function[]>} [param0.undos]
     */
    async unpinChannel({ notify = true, undos = new Map() } = {}) {
        undos.set(this, []);
        this.store.has_unpinned_channels = true;
        // Unpin sub-channels first to prevent onPinStateUpdated of parent from removing
        // isLocallyPinned from them before their values are saved for undo.
        for (const subThread of this.sub_channel_ids) {
            subThread.channel.unpinChannel({ notify: false, undos });
        }
        await this._unpinRegisterUndos(undos.get(this));
        if (!this.exists()) {
            this.store.env.services.notification.add(_t("The conversation was deleted."));
            return;
        }
        await this._unpinExecute();
        if (!this.exists()) {
            this.store.env.services.notification.add(_t("The conversation was deleted."));
            return;
        }
        if (!notify) {
            return;
        }
        const closeFn = this.store.env.services.notification.add(
            this.isHideUntilNewMessageSupported
                ? _t("Conversation hidden until new messages arrive.")
                : _t("Conversation hidden."),
            {
                buttons: [
                    {
                        name: _t("Undo"),
                        onClick: () => {
                            for (const channel of [...undos.keys()].reverse()) {
                                if (channel.exists()) {
                                    for (const fn of undos.get(channel)) {
                                        fn();
                                    }
                                } else {
                                    this.store.env.services.notification.add(
                                        _t("Cannot undo; the conversation was deleted."),
                                        { type: "danger" }
                                    );
                                }
                            }
                            closeFn();
                        },
                    },
                ],
                type: "success",
            }
        );
    }

    async _unpinExecute() {
        this.chatWindow?.close();
        if (this.self_member_id?.is_pinned) {
            await this.pinRpc({ pinned: false });
        }
    }
    /** @param {function[]} undos */
    async _unpinRegisterUndos(undos) {
        if (this.self_member_id?.is_pinned) {
            undos.push(() => {
                if (this.self_member_id) {
                    this.self_member_id.is_pinned = true;
                }
                this.pinRpc({ pinned: true });
            });
        }
        await this.store.chatHub.initPromise;
        if (this.chatWindow) {
            const chatWindowOptions = {
                bypassCompact: this.chatWindow.bypassCompact,
                fromMessagingMenu: this.chatWindow.fromMessagingMenu,
            };
            undos.push(() => this.openChatWindow(chatWindowOptions));
        }
    }

    /** @returns {import("models").ChannelMember[]} */
    _computeOfflineMembers() {
        return this.channel_member_ids.filter((member) => !member.isOnline);
    }
}

DiscussChannel.register();
