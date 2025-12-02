import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/export";
import { useSequential } from "@mail/utils/common/hooks";
import { nearestGreaterThanOrEqual } from "@mail/utils/common/misc";
import { _t } from "@web/core/l10n/translation";

import { formatList } from "@web/core/l10n/utils";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { createElementWithContent } from "@web/core/utils/html";
import { patch } from "@web/core/utils/patch";
import { imageUrl } from "@web/core/utils/urls";

const commandRegistry = registry.category("discuss.channel_commands");

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        /** @type {string} */
        this.avatar_cache_key = undefined;
        this.channel = fields.One("discuss.channel", {
            inverse: "thread",
            /** @this {import("models").Thread} */
            compute() {
                return this.model === "discuss.channel" ? this.id : undefined;
            },
        });
        this.correspondent = fields.One("discuss.channel.member", {
            /** @this {import("models").Thread} */
            compute() {
                return this.computeCorrespondent();
            },
        });
        this.correspondentCountry = fields.One("res.country", {
            /** @this {import("models").Thread} */
            compute() {
                return this.correspondent?.persona?.country_id ?? this.country_id;
            },
        });
        this.group_ids = fields.Many("res.groups");
        this.firstUnreadMessage = fields.One("mail.message", {
            /** @this {import("models").Thread} */
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
                if (!message || this.notEq(message.thread)) {
                    message = nearestGreaterThanOrEqual(messages, separator, (msg) => msg.id);
                }
                return message;
            },
            inverse: "threadAsFirstUnread",
        });
        this.markReadSequential = useSequential();
        this.markedAsUnread = false;
        this.markingAsRead = false;
        /** @type {string} name: only for channel. For generic thread, @see display_name */
        this.name = undefined;
        this.channel_name_member_ids = fields.Many("discuss.channel.member");
        this.self_member_id = fields.One("discuss.channel.member", {
            inverse: "threadAsSelf",
        });
        this.scrollUnread = true;
    },
    get avatarUrl() {
        if (this.channel?.channel_type === "channel" || this.channel?.channel_type === "group") {
            return imageUrl("discuss.channel", this.id, "avatar_128", {
                unique: this.avatar_cache_key,
            });
        }
        if (this.correspondent) {
            return this.correspondent.avatarUrl;
        }
        return super.avatarUrl;
    },
    get showCorrespondentCountry() {
        return false;
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
    /** @returns {import("models").ChannelMember} */
    computeCorrespondent() {
        if (this.channel?.channel_type === "channel") {
            return undefined;
        }
        const correspondents = this.correspondents;
        if (correspondents.length === 1) {
            // 2 members chat.
            return correspondents[0];
        }
        if (correspondents.length === 0 && this.channel?.channel_member_ids.length === 1) {
            // Self-chat.
            return this.channel?.channel_member_ids[0] ?? [];
        }
        return undefined;
    },
    /** @returns {import("models").ChannelMember[]} */
    get correspondents() {
        if (!this.channel) {
            return [];
        }
        return this.channel.channel_member_ids.filter(({ persona }) =>
            persona?.notEq(this.store.self)
        );
    },
    get displayName() {
        if (this.supportsCustomChannelName && this.self_member_id?.custom_channel_name) {
            return this.self_member_id.custom_channel_name;
        }
        if (this.channel?.channel_type === "chat" && this.correspondent) {
            return this.correspondent.name;
        }
        if (this.channel_name_member_ids.length && !this.name) {
            const nameParts = this.channel_name_member_ids
                .sort((m1, m2) => m1.id - m2.id)
                .slice(0, 3)
                .map((member) => member.name);
            if (this.channel?.member_count > 3) {
                const remaining = this.channel.member_count - 3;
                nameParts.push(remaining === 1 ? _t("1 other") : _t("%s others", remaining));
            }
            return formatList(nameParts);
        }
        if (this.model === "discuss.channel" && this.name) {
            return this.name;
        }
        return super.displayName;
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
        if (this.channel?.isChatChannel && this.self_member_id?.message_unread_counter_ui) {
            return this.self_member_id.message_unread_counter_ui;
        }
        if (this.discussAppCategory?.id === "channels") {
            if (this.store.settings.channel_notifications === "no_notif") {
                return 0;
            }
            if (
                this.store.settings.channel_notifications === "all" &&
                !this.self_member_id?.mute_until_dt
            ) {
                return this.self_member_id?.message_unread_counter_ui;
            }
        }
        return super.importantCounter;
    },
    /** @override */
    isDisplayedOnUpdate() {
        super.isDisplayedOnUpdate(...arguments);
        if (!this.self_member_id) {
            return;
        }
        if (!this.isDisplayed) {
            this.self_member_id.new_message_separator_ui =
                this.self_member_id.new_message_separator;
            this.markedAsUnread = false;
        }
    },
    get isUnread() {
        return this.self_member_id?.message_unread_counter > 0 || super.isUnread;
    },
    /** @override */
    markAsRead() {
        super.markAsRead(...arguments);
        if (!this.self_member_id) {
            return;
        }
        const newestPersistentMessage = this.newestPersistentOfAllMessage;
        if (!newestPersistentMessage) {
            return;
        }
        const alreadyReadBySelf =
            this.self_member_id.seen_message_id?.id >= newestPersistentMessage.id &&
            this.self_member_id.new_message_separator > newestPersistentMessage.id;
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
        return this.channel?.isChatChannel
            ? this.self_member_id?.message_unread_counter ?? 0
            : super.needactionCounter;
    },
    /** @override */
    onNewSelfMessage(message) {
        if (!this.self_member_id || message.id < this.self_member_id.seen_message_id?.id) {
            return;
        }
        this.self_member_id.seen_message_id = message;
        this.self_member_id.new_message_separator = message.id + 1;
        this.self_member_id.new_message_separator_ui = this.self_member_id.new_message_separator;
        this.markedAsUnread = false;
    },
    /** @override */
    open(options) {
        if (this.model === "discuss.channel") {
            const res = this.channel.openChannel();
            if (res) {
                return res;
            }
            this.openChatWindow(options);
            return true;
        }
        return super.open(...arguments);
    },
    /** @param {string} body */
    async post(body) {
        const textContent = createElementWithContent("div", body).textContent.trim();
        if (this.model === "discuss.channel" && textContent.startsWith("/")) {
            const [firstWord] = textContent.substring(1).split(/\s/);
            const command = commandRegistry.get(firstWord, false);
            if (
                command &&
                (!command.channel_types ||
                    command.channel_types.includes(this.channel?.channel_type))
            ) {
                await this.executeCommand(command, textContent);
                return;
            }
        }
        return super.post(...arguments);
    },
    get showUnreadBanner() {
        return this.self_member_id?.message_unread_counter_ui > 0;
    },
    get allowedToLeaveChannelTypes() {
        return ["channel", "group"];
    },
    get canLeave() {
        return (
            this.allowedToLeaveChannelTypes.includes(this.channel?.channel_type) &&
            this.group_ids.length === 0 &&
            this.store.self_user
        );
    },
    get allowedToUnpinChannelTypes() {
        return ["chat"];
    },
    get canUnpin() {
        return (
            this.parent_channel_id ||
            this.allowedToUnpinChannelTypes.includes(this.channel?.channel_type)
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
    async leaveChannel() {
        if (this.channel?.channel_type !== "group" && this.create_uid?.eq(this.store.self_user)) {
            await this.askLeaveConfirmation(
                _t("You are the administrator of this channel. Are you sure you want to leave?")
            );
        }
        if (this.channel?.channel_type === "group") {
            await this.askLeaveConfirmation(
                _t(
                    "You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?"
                )
            );
        }
        await this.closeChatWindow();
        this.leaveChannelRpc();
    },
    leaveChannelRpc() {
        this.store.env.services.orm.silent.call("discuss.channel", "action_unfollow", [this.id]);
    },
};
patch(Thread.prototype, threadPatch);
