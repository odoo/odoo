import { Component, onWillStart, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class MoveMessagesDialog extends Component {
    static components = { Dialog };
    static template = "mail.MoveMessagesDialog";
    static props = ["message", "thread", "close?"];

    setup() {
        this.store = useService("mail.store");
        this.orm = useService("orm");
        this.notification = useService("notification");
        const parentThread = this.props.thread.parent_channel_id ?? this.props.thread;
        // Default the thread dropdown to the current sub-channel (if any) so
        // confirming without changes does not silently move to the main channel.
        const sourceSubChannelId = this.props.thread.parent_channel_id
            ? this.props.thread.id
            : false;
        // Exclude the source channel from the target dropdown.
        this.sourceChannelId = parentThread.id;
        this.state = useState({
            channels: [],
            topics: [],
            targetChannelId: parentThread.id,
            targetTopicId: sourceSubChannelId,
            newTopicName: "",
            scope: "only",
            loading: false,
        });
        onWillStart(() => Promise.all([this.loadChannels(), this.loadTopics()]));
    }

    get dialogTitle() {
        const thread = this.props.thread;
        if (thread.parent_channel_id) {
            return _t("Move Messages from %(channel)s / %(thread)s", {
                channel: thread.parent_channel_id.displayName,
                thread: thread.displayName,
            });
        }
        return _t("Move Messages from %(channel)s", { channel: thread.displayName });
    }

    get labels() {
        return {
            channel: _t("New channel"),
            thread: _t("New thread"),
            createNewThread: _t("Create new thread below"),
            newThreadPlaceholder: _t("Type a new thread name (optional)"),
            scope: _t("Which messages should be moved?"),
            cancel: _t("Cancel"),
            confirm: _t("Confirm"),
        };
    }

    get scopeOptions() {
        return [
            { value: "only", label: _t("Move only this message") },
            {
                value: "following",
                label: _t("Move this and all following messages in this thread"),
            },
            { value: "all", label: _t("Move all messages in this thread") },
        ];
    }

    async loadChannels() {
        try {
            this.state.channels = await this.orm.searchRead(
                "discuss.channel",
                [
                    ["channel_type", "=", "channel"],
                    ["parent_channel_id", "=", false],
                    ["id", "!=", this.sourceChannelId],
                ],
                ["id", "name"],
                { order: "name asc" }
            );
        } catch {
            this.state.channels = [];
            this.notification.add(_t("Could not load the list of channels."), { type: "danger" });
        }
    }

    async loadTopics() {
        if (!this.state.targetChannelId) {
            this.state.topics = [];
            return;
        }
        try {
            this.state.topics = await this.orm.searchRead(
                "discuss.channel",
                [["parent_channel_id", "=", this.state.targetChannelId]],
                ["id", "name"],
                { order: "name asc" }
            );
        } catch {
            this.state.topics = [];
            this.notification.add(_t("Could not load the list of threads."), { type: "danger" });
        }
    }

    async onChangeChannel(ev) {
        this.state.targetChannelId = parseInt(ev.target.value, 10) || false;
        this.state.targetTopicId = false;
        await this.loadTopics();
    }

    onChangeTopic(ev) {
        const value = ev.target.value;
        this.state.targetTopicId = value ? parseInt(value, 10) : false;
        if (this.state.targetTopicId) {
            this.state.newTopicName = "";
        }
    }

    onInputNewTopic(ev) {
        this.state.newTopicName = ev.target.value;
        if (this.state.newTopicName) {
            this.state.targetTopicId = false;
        }
    }

    onChangeScope(ev) {
        this.state.scope = ev.target.value;
    }

    get isSameDestination() {
        // A new thread name always targets a brand-new sub-channel.
        if (this.state.newTopicName.trim()) {
            return false;
        }
        const effectiveDestId = this.state.targetTopicId || this.state.targetChannelId;
        return effectiveDestId === this.props.thread.id;
    }

    get canConfirm() {
        return (
            Boolean(this.state.targetChannelId) && !this.state.loading && !this.isSameDestination
        );
    }

    async onConfirm() {
        if (!this.canConfirm) {
            return;
        }
        this.state.loading = true;
        try {
            const { store_data } = await rpc("/discuss/messages/move", {
                message_ids: [this.props.message.id],
                target_channel_id: this.state.targetChannelId,
                scope: this.state.scope,
                new_topic_name: this.state.newTopicName.trim() || false,
                target_sub_channel_id: this.state.targetTopicId || false,
                notify_new: true,
                notify_old: true,
            });
            this.store.insert(store_data);
            this.props.close?.();
        } finally {
            this.state.loading = false;
        }
    }

    onCancel() {
        this.props.close?.();
    }
}
