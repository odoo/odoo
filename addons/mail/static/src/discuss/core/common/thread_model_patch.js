import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { useSequential } from "@mail/utils/common/hooks";
import { compareDatetime, nearestGreaterThanOrEqual } from "@mail/utils/common/misc";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");

/** @type {typeof Thread} */
const threadStaticPatch = {
    async getOrFetch(data, fieldNames = []) {
        if (data.model !== "discuss.channel" || data.id < 1) {
            return super.getOrFetch(...arguments);
        }
        const thread = this.insert({ id: data.id, model: data.model });
        if (thread.fetchChannelInfoState === "fetched") {
            return Promise.resolve(thread);
        }
        if (thread.fetchChannelInfoState === "fetching") {
            return thread.fetchChannelInfoDeferred;
        }
        thread.fetchChannelInfoState = "fetching";
        const def = new Deferred();
        thread.fetchChannelInfoDeferred = def;
        this.store.fetchChannel(thread.id).then(
            () => {
                if (thread.exists()) {
                    thread.fetchChannelInfoState = "fetched";
                    thread.fetchChannelInfoDeferred = undefined;
                    def.resolve(thread);
                } else {
                    def.resolve();
                }
            },
            () => {
                if (thread.exists()) {
                    thread.fetchChannelInfoState = "not_fetched";
                    thread.fetchChannelInfoDeferred = undefined;
                    def.reject(thread);
                } else {
                    def.reject();
                }
            }
        );
        return def;
    },
};
patch(Thread, threadStaticPatch);

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        this.channel = fields.One("discuss.channel", {
            compute() {
                if (this.model === "discuss.channel") {
                    return {
                        id: this.id,
                        name: this.name,
                        member_count: this.member_count,
                        channel_type: this.channel?.channel_type,
                    };
                }
            },
            inverse: "thread",
        });
        /** @type {"video_full_screen"|undefined} */
        this.default_display_mode = undefined;
        this.displayToSelf = fields.Attr(false, {
            compute() {
                return (
                    this.is_pinned ||
                    (["channel", "group"].includes(this.channel_type) &&
                        this.hasSelfAsMember &&
                        !this.parent_channel_id)
                );
            },
            onUpdate() {
                this.onPinStateUpdated();
            },
        });
        /** @type {Deferred<Thread|undefined>} */
        this.fetchChannelInfoDeferred = undefined;
        /** @type {"not_fetched"|"fetching"|"fetched"} */
        this.fetchChannelInfoState = "not_fetched";
        this.group_ids = fields.Many("res.groups");
        /** @type {"not_fetched"|"pending"|"fetched"} */
        this.fetchMembersState = "not_fetched";
        this.firstUnreadMessage = fields.One("mail.message", {
            /** @this {import("models").Thread} */
            compute() {
                if (!this.channel?.selfMember) {
                    return null;
                }
                const messages = this.messages.filter((m) => !m.isNotification);
                const separator = this.channel.selfMember.new_message_separator_ui;
                if (separator === 0 && !this.loadOlder) {
                    return messages[0];
                }
                if (!separator || messages.length === 0 || messages.at(-1).id < separator) {
                    return null;
                }
                // try to find a perfect match according to the member's separator
                let message = this.store["mail.message"].get({ id: separator });
                if (!message || this.notEq(message.thread)) {
                    message = nearestGreaterThanOrEqual(messages, separator, (msg) => msg.id);
                }
                return message;
            },
            inverse: "threadAsFirstUnread",
        });
        this.invited_member_ids = fields.Many("discuss.channel.member");
        /** @type {Boolean} */
        this.isLocallyPinned = fields.Attr(false, {
            onUpdate() {
                this.onPinStateUpdated();
            },
        });
        this.last_interest_dt = fields.Datetime();
        this.lastInterestDt = fields.Datetime({
            /** @this {import("models").Thread} */
            compute() {
                const selfMemberLastInterestDt = this.channel.selfMember?.last_interest_dt;
                const lastInterestDt = this.last_interest_dt;
                return compareDatetime(selfMemberLastInterestDt, lastInterestDt) > 0
                    ? selfMemberLastInterestDt
                    : lastInterestDt;
            },
        });
        this.markReadSequential = useSequential();
        this.markedAsUnread = false;
        this.markingAsRead = false;
        this.mute_until_dt = fields.Datetime();
        this.scrollUnread = true;
        this.toggleBusSubscription = fields.Attr(false, {
            /** @this {import("models").Thread} */
            compute() {
                return (
                    this.model === "discuss.channel" &&
                    this.channel.selfMember?.memberSince >= this.store.env.services.bus_service.startedAt
                );
            },
            onUpdate() {
                this.store.updateBusSubscription();
            },
        });
    },
    get allowDescription() {
        return ["channel", "group"].includes(this.channel_type);
    },
    get allowedToLeaveChannelTypes() {
        return ["channel", "group"];
    },
    get allowedToUnpinChannelTypes() {
        return ["chat"];
    },
    get canLeave() {
        return (
            this.allowedToLeaveChannelTypes.includes(this.channel?.channel_type) &&
            this.group_ids.length === 0 &&
            this.store.self?.type === "partner"
        );
    },
    get canUnpin() {
        return (
            this.parent_channel_id || this.allowedToUnpinChannelTypes.includes(this.channel_type)
        );
    },
    executeCommand(command, body = "") {
        return this.store.env.services.orm.call(
            "discuss.channel",
            command.methodName,
            [[this.id]],
            { body }
        );
    },
    async fetchChannelMembers() {
        if (this.fetchMembersState === "pending") {
            return;
        }
        const previousState = this.fetchMembersState;
        this.fetchMembersState = "pending";
        let data;
        try {
            data = await rpc("/discuss/channel/members", {
                channel_id: this.id,
                known_member_ids: this.channel.channel_member_ids.map((channelMember) => channelMember.id),
            });
        } catch (e) {
            this.fetchMembersState = previousState;
            throw e;
        }
        this.fetchMembersState = "fetched";
        this.store.insert(data);
    },
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
            const { "ir.attachment": attachments = [] } = this.store.insert(data);
            if (attachments.length < limit) {
                this.areAttachmentsLoaded = true;
            }
        } finally {
            this.isLoadingAttachments = false;
        }
    },
    get hasAttachmentPanel() {
        return this.model === "discuss.channel";
    },
    get hasMemberList() {
        return ["channel", "group"].includes(this.channel_type);
    },
    get hasSelfAsMember() {
        return Boolean(this.channel.selfMember);
    },
    /** @override */
    get importantCounter() {
        if (this.isChatChannel && this.channel.selfMember?.message_unread_counter_ui) {
            return this.channel.selfMember.message_unread_counter_ui;
        }
        return super.importantCounter;
    },
    get invitationLink() {
        if (!this.uuid || this.channel_type === "chat") {
            return undefined;
        }
        return `${window.location.origin}/chat/${this.id}/${this.uuid}`;
    },
    /** @override */
    isDisplayedOnUpdate() {
        super.isDisplayedOnUpdate(...arguments);
        if (!this.channel?.selfMember) {
            return;
        }
        if (!this.isDisplayed) {
            this.channel.selfMember.new_message_separator_ui = this.channel.selfMember.new_message_separator;
            this.markedAsUnread = false;
        }
    },
    get isChatChannel() {
        return ["chat", "group"].includes(this.channel_type);
    },
    get isMuted() {
        return this.mute_until_dt;
    },
    get isUnread() {
        return this.channel.selfMember?.message_unread_counter > 0 || super.isUnread;
    },
    async leave() {
        await this.store.env.services.orm.silent.call("discuss.channel", "action_unfollow", [
            this.id,
        ]);
    },
    async leaveChannel({ force = false } = {}) {
        if (
            this.channel_type !== "group" &&
            this.create_uid?.eq(this.store.self.main_user_id) &&
            !force
        ) {
            await this.askLeaveConfirmation(
                _t("You are the administrator of this channel. Are you sure you want to leave?")
            );
        }
        if (this.channel_type === "group" && !force) {
            await this.askLeaveConfirmation(
                _t(
                    "You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?"
                )
            );
        }
        this.leave();
    },
    async markAsFetched() {
        await this.store.env.services.orm.silent.call("discuss.channel", "channel_fetched", [
            [this.id],
        ]);
    },
    /** @override */
    markAsRead() {
        super.markAsRead(...arguments);
        if (!this.channel.selfMember) {
            return;
        }
        const newestPersistentMessage = this.newestPersistentOfAllMessage;
        if (!newestPersistentMessage) {
            return;
        }
        const alreadyReadBySelf =
            this.channel.selfMember.seen_message_id?.id >= newestPersistentMessage.id &&
            this.channel.selfMember.new_message_separator > newestPersistentMessage.id;
        if (alreadyReadBySelf) {
            return;
        }
        this.markReadSequential(async () => {
            this.markingAsRead = true;
            return rpc(
                "/discuss/channel/mark_as_read",
                {
                    channel_id: this.id,
                    last_message_id: newestPersistentMessage.id,
                },
                { silent: true }
            ).catch((e) => {
                if (e.code !== 404) {
                    throw e;
                }
            });
        }).then(() => (this.markingAsRead = false));
    },
    /**
     * To be overridden.
     * The purpose is to exclude technical channel_member_ids like bots and avoid
     * "wrong" seen message indicator
     * @returns {import("models").ChannelMember[]}
     */
    get membersThatCanSeen() {
        return this.channel.channel_member_ids;
    },
    /** @override */
    get needactionCounter() {
        return this.isChatChannel
            ? this.channel.selfMember?.message_unread_counter ?? 0
            : super.needactionCounter;
    },
    /** @param {string} data base64 representation of the binary */
    async notifyAvatarToServer(data) {
        await rpc("/discuss/channel/update_avatar", {
            channel_id: this.id,
            data,
        });
    },
    async notifyDescriptionToServer(description) {
        this.description = description;
        return this.store.env.services.orm.call(
            "discuss.channel",
            "channel_change_description",
            [[this.id]],
            { description }
        );
    },
    /** @override */
    onNewSelfMessage(message) {
        if (!this.channel?.selfMember || message.id < this.channel.selfMember.seen_message_id?.id) {
            return;
        }
        this.channel.selfMember.seen_message_id = message;
        this.channel.selfMember.new_message_separator = message.id + 1;
        this.channel.selfMember.new_message_separator_ui = this.channel.selfMember.new_message_separator;
        this.markedAsUnread = false;
    },
    pin() {
        if (this.model !== "discuss.channel" || this.store.self.type !== "partner") {
            return;
        }
        this.is_pinned = true;
        return this.store.env.services.orm.silent.call(
            "discuss.channel",
            "channel_pin",
            [this.id],
            { pinned: true }
        );
    },
    /** @param {string} body */
    async post(body) {
        if (this.model === "discuss.channel" && body.startsWith("/")) {
            const [firstWord] = body.substring(1).split(/\s/);
            const command = commandRegistry.get(firstWord, false);
            if (
                command &&
                (!command.channel_types || command.channel_types.includes(this.channel_type))
            ) {
                await this.executeCommand(command, body);
                return;
            }
        }
        return super.post(...arguments);
    },
    /** @param {string} name */
    async rename(name) {
        const newName = name.trim();
        if (
            newName !== this.displayName &&
            ((newName && this.channel_type === "channel") || this.isChatChannel)
        ) {
            if (this.channel_type === "channel" || this.channel_type === "group") {
                this.name = newName;
                await this.store.env.services.orm.call(
                    "discuss.channel",
                    "channel_rename",
                    [[this.id]],
                    { name: newName }
                );
            } else if (this.supportsCustomChannelName) {
                if (this.channel.selfMember) {
                    this.channel.selfMember.custom_channel_name = newName;
                }
                await this.store.env.services.orm.call(
                    "discuss.channel",
                    "channel_set_custom_name",
                    [[this.id]],
                    { name: newName }
                );
            }
        }
    },
    get showCorrespondentCountry() {
        return false;
    },
    get showUnreadBanner() {
        return this.channel?.selfMember?.message_unread_counter_ui > 0;
    },
    get typesAllowingCalls() {
        return ["chat", "channel", "group"];
    },
};
patch(Thread.prototype, threadPatch);
