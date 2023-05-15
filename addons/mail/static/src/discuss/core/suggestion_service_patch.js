/* @odoo-module */

import { SuggestionService, suggestionService } from "@mail/composer/suggestion_service";
import { cleanTerm } from "@mail/utils/format";
import { createLocalId } from "@mail/utils/misc";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");

patch(SuggestionService.prototype, "discuss", {
    setup(env, services) {
        this._super(...arguments);
        /** @type {import("@mail/discuss/channel_member_service").ChannelMemberService} */
        this.channelMemberService = services["discuss.channel.member"];
        /** @type {import("@mail/discuss/discuss_store_service").DiscusStore} */
        this.discussStore = services["discuss.store"];
    },
    getSupportedDelimiters(thread) {
        const res = this._super(thread);
        return thread?.model === "discuss.channel" ? [...res, ["/", 0]] : res;
    },
    /**
     * @override
     */
    searchSuggestions({ delimiter, term }, { thread } = {}, sort = false) {
        const cleanedSearchTerm = cleanTerm(term);
        switch (delimiter) {
            case "/":
                return this.searchChannelCommand(cleanedSearchTerm, thread, sort);
            case "#":
                return this.searchChannelSuggestions(cleanedSearchTerm, thread, sort);
        }
        return this._super(...arguments);
    },
    searchChannelCommand(cleanedSearchTerm, thread, sort) {
        if (!thread.isChannel) {
            // channel commands are channel specific
            return;
        }
        const commands = commandRegistry
            .getEntries()
            .filter(([name, command]) => {
                if (!cleanTerm(name).includes(cleanedSearchTerm)) {
                    return false;
                }
                if (command.channel_types) {
                    return command.channel_types.includes(thread.type);
                }
                return true;
            })
            .map(([name, command]) => {
                return {
                    channel_types: command.channel_types,
                    help: command.help,
                    id: command.id,
                    name,
                };
            });
        const sortFunc = (c1, c2) => {
            if (c1.channel_types && !c2.channel_types) {
                return -1;
            }
            if (!c1.channel_types && c2.channel_types) {
                return 1;
            }
            const cleanedName1 = cleanTerm(c1.name || "");
            const cleanedName2 = cleanTerm(c2.name || "");
            if (
                cleanedName1.startsWith(cleanedSearchTerm) &&
                !cleanedName2.startsWith(cleanedSearchTerm)
            ) {
                return -1;
            }
            if (
                !cleanedName1.startsWith(cleanedSearchTerm) &&
                cleanedName2.startsWith(cleanedSearchTerm)
            ) {
                return 1;
            }
            if (cleanedName1 < cleanedName2) {
                return -1;
            }
            if (cleanedName1 > cleanedName2) {
                return 1;
            }
            return c1.id - c2.id;
        };
        return {
            type: "ChannelCommand",
            mainSuggestions: sort ? commands.sort(sortFunc) : commands,
        };
    },

    searchChannelSuggestions(cleanedSearchTerm, thread, sort) {
        let threads;
        if (
            thread &&
            (thread.type === "group" ||
                thread.type === "chat" ||
                (thread.type === "channel" && thread.authorizedGroupFullName))
        ) {
            // Only return the current channel when in the context of a
            // group restricted channel or group or chat. Indeed, the message with the mention
            // would appear in the target channel, so this prevents from
            // inadvertently leaking the private message into the mentioned
            // channel.
            threads = [thread];
        } else {
            threads = Object.values(this.store.threads);
        }
        const suggestionList = threads.filter(
            (thread) =>
                thread.type === "channel" &&
                thread.displayName &&
                cleanTerm(thread.displayName).includes(cleanedSearchTerm)
        );
        const sortFunc = (c1, c2) => {
            const isPublicChannel1 = c1.type === "channel" && !c2.authorizedGroupFullName;
            const isPublicChannel2 = c2.type === "channel" && !c2.authorizedGroupFullName;
            const c1HasSelfAsMember =
                this.discussStore.channels[createLocalId("discuss.channel", c1.id)].hasSelfAsMember;
            const c2HasSelfAsMember =
                this.discussStore.channels[createLocalId("discuss.channel", c2.id)].hasSelfAsMember;

            if (isPublicChannel1 && !isPublicChannel2) {
                return -1;
            }
            if (!isPublicChannel1 && isPublicChannel2) {
                return 1;
            }
            if (c1HasSelfAsMember && !c2HasSelfAsMember) {
                return -1;
            }
            if (!c1HasSelfAsMember && c2HasSelfAsMember) {
                return 1;
            }
            const cleanedDisplayName1 = cleanTerm(c1.displayName ?? "");
            const cleanedDisplayName2 = cleanTerm(c2.displayName ?? "");
            if (
                cleanedDisplayName1.startsWith(cleanedSearchTerm) &&
                !cleanedDisplayName2.startsWith(cleanedSearchTerm)
            ) {
                return -1;
            }
            if (
                !cleanedDisplayName1.startsWith(cleanedSearchTerm) &&
                cleanedDisplayName2.startsWith(cleanedSearchTerm)
            ) {
                return 1;
            }
            if (cleanedDisplayName1 < cleanedDisplayName2) {
                return -1;
            }
            if (cleanedDisplayName1 > cleanedDisplayName2) {
                return 1;
            }
            return c1.id - c2.id;
        };
        return {
            type: "Thread",
            mainSuggestions: sort ? suggestionList.sort(sortFunc) : suggestionList,
        };
    },
    /**
     * @override
     * @param {string} term
     * @param {import("@mail/core/thread_model").Thread} thread
     */
    async fetchPartners(term, thread) {
        if (thread.model !== "discuss.channel") {
            this._super(...arguments);
        } else {
            const kwargs = { search: term };
            kwargs.channel_id = thread.id;
            const suggestedPartners = await this.orm.call(
                "res.partner",
                "get_mention_suggestions_from_channel",
                [],
                kwargs
            );
            suggestedPartners.map((data) => {
                this.personaService.insert({ ...data, type: "partner" });
                if (data.persona?.channelMembers) {
                    this.channelMemberService.insert(...data.persona.channelMembers);
                }
            });
        }
    },
    /**
     * @override
     * @param {import("@mail/core/thread_model").Thread} thread
     */
    partnersToSearch(thread) {
        let partners;
        const isNonPublicChannel =
            thread &&
            (thread.type === "group" ||
                thread.type === "chat" ||
                (thread.type === "channel" && thread.group_based_subscription));
        if (isNonPublicChannel) {
            // Only return the channel members when in the context of a
            // group restricted channel. Indeed, the message with the mention
            // would be notified to the mentioned partner, so this prevents
            // from inadvertently leaking the private message to the
            // mentioned partner.
            const channel = this.discussStore.channels[createLocalId("discuss.channel", thread.id)];
            partners = channel.channelMembers
                .map((member) => member.persona)
                .filter((persona) => persona.type === "partner");
        } else {
            partners = this._super(...arguments);
        }
        return partners;
    },
    /**
     * @override
     * @param {import("@mail/core/thread_model").Thread} thread
     * @param {import('@mail/core/persona_model').Persona} p1
     * @param {import('@mail/core/persona_model').Persona} p2
     * @param {string} cleanedSearchTerm to compare in non channel thread
     */
    compareSuggestions(p1, p2, thread, cleanedSearchTerm) {
        const channel = this.discussStore.channels[createLocalId("discuss.channel", thread.id)];
        if (p1.user?.isInternalUser == p2.user?.isInternalUser && thread.type === "channel") {
            const isMember1 = channel.channelMembers.some((member) => member.persona === p1);
            const isMember2 = channel.channelMembers.some((member) => member.persona === p2);
            if (isMember1 && !isMember2) {
                return -1;
            }
            if (!isMember1 && isMember2) {
                return 1;
            }
        }
        return this._super(...arguments);
    },
});

patch(suggestionService, "discuss", {
    dependencies: [...suggestionService.dependencies, "discuss.store"],
});
