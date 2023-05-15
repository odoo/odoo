/* @odoo-module */

import { ThreadService, threadService } from "@mail/core/thread_service";
import { Channel } from "@mail/discuss/channel_model";
import { onChange, createLocalId } from "@mail/utils/misc";
import { removeFromArray } from "@mail/utils/arrays";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");

patch(ThreadService.prototype, "discuss", {
    setup(env, services) {
        this._super(env, services);
        /** @type {import("@mail/discuss/channel_member_service").ChannelMemberService} */
        this.channelMemberService = services["discuss.channel.member"];
        /** @type {import("@mail/discuss/discuss_store_service").DiscusStore} */
        this.discussStore = services["discuss.store"];
    },
    /**
     * @override
     * @param {import("@mail/core/thread_model").Thread} thread
     * @param {string} body
     */
    async post(thread, body) {
        if (thread.model === "discuss.channel" && body.startsWith("/")) {
            const [firstWord] = body.substring(1).split(/\s/);
            const command = commandRegistry.get(firstWord, false);
            if (
                command &&
                (!command.channel_types || command.channel_types.includes(thread.type))
            ) {
                await this.executeCommand(thread, command, body);
                return;
            }
        }
        return this._super(...arguments);
    },
    /**
     * @override
     * @param {import("@mail/core/thread_model").Thread} thread
     */
    onchangeThread(thread) {
        this._super(...arguments);
        onChange(thread, "is_pinned", () => {
            if (!thread.is_pinned && this.store.discuss.threadLocalId === thread.localId) {
                this.store.discuss.threadLocalId = null;
            }
        });
    },
    /**
     * @override
     * @param {import("@mail/core/thread_model").Thread} thread
     * @param {Object} data
     */
    update(thread, data) {
        this._super(...arguments);
        const { ...serverData } = data;
        if (serverData) {
            if (thread.model === "discuss.channel") {
                const localId = createLocalId(thread.model, thread.id);
                let channel = this.discussStore.channels[localId];
                if (!channel) {
                    const localId = createLocalId(thread.model, thread.id);
                    this.discussStore.channels[localId] = new Channel();
                    channel = this.discussStore.channels[localId];
                    channel.discussStore = this.discussStore;
                }
                onChange(channel, "channelMembers", () =>
                    this.discussStore.updateBusSubscription()
                );
                channel.memberCount = serverData.channel?.memberCount ?? channel.memberCount;
                Object.assign(channel, thread);
                if (serverData.channel?.channelMembers) {
                    for (const [command, membersData] of serverData.channel.channelMembers) {
                        const members = Array.isArray(membersData) ? membersData : [membersData];
                        for (const memberData of members) {
                            const member = this.channelMemberService.insert([command, memberData]);
                            if (channel.type !== "chat") {
                                continue;
                            }
                            if (
                                member.persona.id !== channel._store.user?.id ||
                                (serverData.channel.channelMembers[0][1].length === 1 &&
                                    member.persona.id === channel._store.user?.id)
                            ) {
                                thread.chatPartnerId = member.persona.id;
                            }
                        }
                    }
                }
                if ("rtc_inviting_session" in serverData) {
                    this.env.bus.trigger("THREAD-SERVICE:UPDATE_RTC_SESSIONS", {
                        channel,
                        record: serverData.rtc_inviting_session,
                    });
                    channel.invitingRtcSessionId = serverData.rtc_inviting_session.id;
                    if (!this.discussStore.ringingThreads.includes(channel.localId)) {
                        this.discussStore.ringingThreads.push(channel.localId);
                    }
                }
                if ("rtcInvitingSession" in serverData) {
                    if (Array.isArray(serverData.rtcInvitingSession)) {
                        if (serverData.rtcInvitingSession[0][0] === "unlink") {
                            channel.invitingRtcSessionId = undefined;
                            removeFromArray(this.discussStore.ringingThreads, channel.localId);
                        }
                        return;
                    }
                    this.env.bus.trigger("THREAD-SERVICE:UPDATE_RTC_SESSIONS", {
                        channel,
                        record: serverData.rtcInvitingSession,
                    });
                    channel.invitingRtcSessionId = serverData.rtcInvitingSession.id;
                    this.discussStore.ringingThreads.push(channel.localId);
                }
                if (channel.type === "chat" && serverData.channel) {
                    thread.customName = serverData.channel.custom_channel_name;
                }
                if ("rtcSessions" in serverData) {
                    this.env.bus.trigger("THREAD-SERVICE:UPDATE_RTC_SESSIONS", {
                        channel,
                        commands: serverData.rtcSessions,
                    });
                }
                if ("invitedMembers" in serverData) {
                    if (!serverData.invitedMembers) {
                        channel.invitedMemberIds.clear();
                        return;
                    }
                    const command = serverData.invitedMembers[0][0];
                    const members = serverData.invitedMembers[0][1];
                    switch (command) {
                        case "insert":
                            if (members) {
                                for (const member of members) {
                                    const record = this.channelMemberService.insert(member);
                                    channel.invitedMemberIds.add(record.id);
                                }
                            }
                            break;
                        case "unlink":
                        case "insert-and-unlink":
                            // eslint-disable-next-line no-case-declarations
                            for (const member of members) {
                                channel.invitedMemberIds.delete(member.id);
                            }
                            break;
                    }
                }
            }
        }
    },
    async fetchChannelMembers(channel) {
        const known_member_ids = channel.channelMembers.map((channelMember) => channelMember.id);
        const results = await this.rpc("/discuss/channel/members", {
            channel_id: channel.id,
            known_member_ids: known_member_ids,
        });
        let channelMembers = [];
        if (
            results["channelMembers"] &&
            results["channelMembers"][0] &&
            results["channelMembers"][0][1]
        ) {
            channelMembers = results["channelMembers"][0][1];
        }
        channel.memberCount = results["memberCount"];
        for (const channelMember of channelMembers) {
            if (channelMember.persona || channelMember.partner) {
                this.channelMemberService.insert({ ...channelMember, channelId: channel.id });
            }
        }
    },
    /**
     * @override
     * @param {import("@mail/core/thread_model").Thread} thread
     */
    remove(thread) {
        this._super(...arguments);
        delete this.discussStore.channels[thread.localId];
    },
});

patch(threadService, "discuss", {
    dependencies: [...threadService.dependencies, "discuss.store"],
});
