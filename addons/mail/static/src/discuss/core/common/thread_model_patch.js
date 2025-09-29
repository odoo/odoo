import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { useSequential } from "@mail/utils/common/hooks";
import { compareDatetime, nearestGreaterThanOrEqual } from "@mail/utils/common/misc";
import { _t } from "@web/core/l10n/translation";

import { formatList } from "@web/core/l10n/utils";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { createElementWithContent } from "@web/core/utils/html";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");

/** @type {typeof Thread} */
const threadStaticPatch = {
    async getOrFetch(data, fieldNames = []) {
        if (data.model !== "discuss.channel" || data.id < 1) {
            return super.getOrFetch(...arguments);
        }
        const thread = this.store.Thread.get({ id: data.id, model: data.model });
        if (thread?.fetchChannelInfoState === "fetched") {
            return Promise.resolve(thread);
        }
        const fetchChannelInfoDeferred = this.store.channelIdsFetchingDeferred.get(data.id);
        if (fetchChannelInfoDeferred) {
            return fetchChannelInfoDeferred;
        }
        const def = new Deferred();
        this.store.channelIdsFetchingDeferred.set(data.id, def);
        this.store.fetchChannel(data.id).then(
            () => {
                this.store.channelIdsFetchingDeferred.delete(data.id);
                const thread = this.store.Thread.get({ id: data.id, model: data.model });
                if (thread?.exists()) {
                    thread.fetchChannelInfoState = "fetched";
                    def.resolve(thread);
                } else {
                    def.resolve();
                }
            },
            () => {
                this.store.channelIdsFetchingDeferred.delete(data.id);
                const thread = this.store.Thread.get({ id: data.id, model: data.model });
                if (thread?.exists()) {
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
            inverse: "thread",
            compute() {
                if (this.model === "discuss.channel") {
                    return {
                        id: this.id,
                        channel_member_ids: this.channel_member_ids,
                        channel_type: this.channel_type,
                        member_count: this.member_count,
                        self_member_id: this.self_member_id,
                        typingMembers: this.typingMembers,
                        avatar_cache_key: this.avatar_cache_key,
                        firstUnreadMessage: this.firstUnreadMessage,
                        default_display_mode: this.default_display_mode,
                        country_id: this.country_id,
                    };
                }
                return undefined;
            },
            onDelete: (r) => r.delete(),
        });
        this.channel_member_ids = fields.Many("discuss.channel.member", {
            inverse: "channel_id",
            onDelete: (r) => r.delete(),
            sort: (m1, m2) => m1.id - m2.id,
        });
        this.self_member_id = fields.One("discuss.channel.member", {
            inverse: "threadAsSelf",
        });
        /** @type {"video_full_screen"|undefined} */
        this.default_display_mode = undefined;
        /** @type {Deferred<Thread|undefined>} */
        this.fetchChannelInfoDeferred = undefined;
        /** @type {"not_fetched"|"fetching"|"fetched"} */
        this.fetchChannelInfoState = "not_fetched";
        this.group_ids = fields.Many("res.groups");
        this.firstUnreadMessage = fields.One("mail.message", {
            /** @this {import("models").Thread} */
            compute() {
                if (!this.channel?.self_member_id) {
                    return null;
                }
                const messages = this.messages.filter((m) => !m.isNotification);
                const separator = this.channel?.self_member_id.new_message_separator_ui;
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
        this.last_interest_dt = fields.Datetime();
        this.lastInterestDt = fields.Datetime({
            /** @this {import("models").Thread} */
            compute() {
                const selfMemberLastInterestDt = this.channel?.self_member_id?.last_interest_dt;
                const lastInterestDt = this.last_interest_dt;
                return compareDatetime(selfMemberLastInterestDt, lastInterestDt) > 0
                    ? selfMemberLastInterestDt
                    : lastInterestDt;
            },
        });
        this.markReadSequential = useSequential();
        this.markedAsUnread = false;
        this.markingAsRead = false;
        /** @type {number|undefined} */
        this.member_count = undefined;
        /** @type {string} name: only for channel. For generic thread, @see display_name */
        this.name = undefined;
        this.channel_name_member_ids = fields.Many("discuss.channel.member");
        this.scrollUnread = true;
        this.toggleBusSubscription = fields.Attr(false, {
            /** @this {import("models").Thread} */
            compute() {
                return (
                    this.model === "discuss.channel" &&
                    this.channel?.self_member_id?.memberSince >=
                        this.store.env.services.bus_service.startedAt
                );
            },
            onUpdate() {
                this.store.updateBusSubscription();
            },
        });
        this.typingMembers = fields.Many("discuss.channel.member", { inverse: "threadAsTyping" });
    },

    /** @override */
    async checkReadAccess() {
        const res = await super.checkReadAccess();
        if (!res && this.model === "discuss.channel") {
            // channel is assumed to be readable if its channel_type is known
            return this.channel.channel_type;
        }
        return res;
    },
    get displayName() {
        if (this.supportsCustomChannelName && this.channel?.self_member_id?.custom_channel_name) {
            return this.channel?.self_member_id.custom_channel_name;
        }
        if (this.channel?.channel_type === "chat" && this.channel?.correspondent) {
            return this.channel.correspondent.name;
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
        if (this.model === "discuss.channel" && this.name) {
            return this.name;
        }
        return super.displayName;
    },
    async fetchChannelMembers() {
        if (this.fetchMembersState === "pending") {
            return;
        }
        const previousState = this.fetchMembersState;
        this.fetchMembersState = "pending";
        const known_member_ids = this.channel?.channel_member_ids.map(
            (channelMember) => channelMember.id
        );
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
            this.store.insert(data.store_data);
            if (data.count < limit) {
                this.areAttachmentsLoaded = true;
            }
        } finally {
            this.isLoadingAttachments = false;
        }
    },
    /** @override */
    get importantCounter() {
        if (this.isChatChannel && this.channel?.self_member_id?.message_unread_counter_ui) {
            return this.channel?.self_member_id.message_unread_counter_ui;
        }
        if (this.discussAppCategory?.id === "channels") {
            if (this.store.settings.channel_notifications === "no_notif") {
                return 0;
            }
            if (
                this.store.settings.channel_notifications === "all" &&
                !this.channel?.self_member_id?.mute_until_dt
            ) {
                return this.channel?.self_member_id?.message_unread_counter_ui;
            }
        }
        return super.importantCounter;
    },
    /** @override */
    isDisplayedOnUpdate() {
        super.isDisplayedOnUpdate(...arguments);
        if (!this.channel?.self_member_id) {
            return;
        }
        if (!this.isDisplayed) {
            this.channel.self_member_id.new_message_separator_ui =
                this.channel?.self_member_id.new_message_separator;
            this.markedAsUnread = false;
        }
    },
    get isUnread() {
        return this.channel?.self_member_id?.message_unread_counter > 0 || super.isUnread;
    },
    /** @override */
    markAsRead() {
        super.markAsRead(...arguments);
        if (!this.channel?.self_member_id) {
            return;
        }
        const newestPersistentMessage = this.newestPersistentOfAllMessage;
        if (!newestPersistentMessage) {
            return;
        }
        const alreadyReadBySelf =
            this.channel?.self_member_id.seen_message_id?.id >= newestPersistentMessage.id &&
            this.channel?.self_member_id.new_message_separator > newestPersistentMessage.id;
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
    /** @override */
    get needactionCounter() {
        return this.isChatChannel
            ? this.channel?.self_member_id?.message_unread_counter ?? 0
            : super.needactionCounter;
    },
    /** @override */
    onNewSelfMessage(message) {
        if (
            !this.channel?.self_member_id ||
            message.id < this.channel?.self_member_id.seen_message_id?.id
        ) {
            return;
        }
        this.channel.self_member_id.seen_message_id = message;
        this.channel.self_member_id.new_message_separator = message.id + 1;
        this.channel.self_member_id.new_message_separator_ui =
            this.channel?.self_member_id.new_message_separator;
        this.markedAsUnread = false;
    },
    /** @override */
    open(options) {
        if (this.model === "discuss.channel") {
            if (!this.channel?.self_member_id) {
                this.store.env.services["bus_service"].addChannel(this.busChannel);
            }
            const res = this.openChannel();
            if (res) {
                return res;
            }
            this.openChatWindow(options);
            return true;
        }
        return super.open(...arguments);
    },
    /**
     * @returns {boolean} true if the channel was opened, false otherwise
     */
    openChannel() {
        return false;
    },
    /** @param {string} body */
    async post(body) {
        const textContent = createElementWithContent("div", body).textContent.trim();
        if (this.model === "discuss.channel" && textContent.startsWith("/")) {
            const [firstWord] = textContent.substring(1).split(/\s/);
            const command = commandRegistry.get(firstWord, false);
            if (
                command &&
                (!command.channel_types || command.channel_types.includes(this.channel_type))
            ) {
                await this.executeCommand(command, textContent);
                return;
            }
        }
        return super.post(...arguments);
    },
    get showUnreadBanner() {
        return this.channel?.self_member_id?.message_unread_counter_ui > 0;
    },
    get unknownMembersCount() {
        return (this.member_count ?? 0) - this.channel?.channel_member_ids.length;
    },
    get allowedToLeaveChannelTypes() {
        return ["channel", "group"];
    },
    get canLeave() {
        return (
            this.allowedToLeaveChannelTypes.includes(this.channel_type) &&
            this.group_ids.length === 0 &&
            this.store.self_partner
        );
    },
    get allowedToUnpinChannelTypes() {
        return ["chat"];
    },
    get canUnpin() {
        return (
            this.parent_channel_id || this.allowedToUnpinChannelTypes.includes(this.channel_type)
        );
    },
    get typesAllowingCalls() {
        return ["chat", "channel", "group"];
    },
    get allowCalls() {
        return (
            !this.isTransient &&
            this.typesAllowingCalls.includes(this.channel_type) &&
            !this.channel?.correspondent?.persona.eq(this.store.odoobot)
        );
    },
    get isChatChannel() {
        return ["chat", "group"].includes(this.channel_type);
    },
    get allowDescription() {
        return ["channel", "group"].includes(this.channel_type);
    },
    get invitationLink() {
        if (!this.uuid || this.channel_type === "chat") {
            return undefined;
        }
        return `${window.location.origin}/chat/${this.id}/${this.uuid}`;
    },
    executeCommand(command, body = "") {
        return this.store.env.services.orm.call(
            "discuss.channel",
            command.methodName,
            [[this.id]],
            { body }
        );
    },
    async markAsFetched() {
        await this.store.env.services.orm.silent.call("discuss.channel", "channel_fetched", [
            [this.id],
        ]);
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
        await this.closeChatWindow();
        await this.store.env.services.orm.silent.call("discuss.channel", "action_unfollow", [
            this.id,
        ]);
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
                if (this.channel?.self_member_id) {
                    this.channel.self_member_id.custom_channel_name = newName;
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
};
patch(Thread.prototype, threadPatch);
