import { cleanTerm } from "@mail/utils/common/format";

import { Component, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ImStatus } from "@mail/core/common/im_status";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { ChannelInvitation } from "../common/channel_invitation";

const commandSetupRegistry = registry.category("command_setup");
const commandProviderRegistry = registry.category("command_provider");

const NEW_CHANNEL = "NEW_CHANNEL";
const NEW_GROUP_CHAT = "NEW_GROUP_CHAT";

class CreateChatDialog extends Component {
    static components = { ChannelInvitation, Dialog };
    static props = ["close", "name?"];
    static template = "mail.CreateChatDialog";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.invitePeopleState = useState({
            selectablePartners: [],
            selectedPartners: [],
            searchStr: this.props.name,
        });
    }

    get createText() {
        if (this.invitePeopleState.selectedPartners.length === 1) {
            return _t("Open Chat");
        }
        return _t("Create Group Chat");
    }

    onClickConfirm() {
        const selectedPartnersId = this.invitePeopleState.selectedPartners.map((p) => p.id);
        const partners_to = [...new Set([this.store.self.id, ...selectedPartnersId])];
        if (partners_to.length === 1) {
            this.store.createGroupChat({ partners_to });
        } else {
            this.store.startChat(partners_to);
        }
        this.props.close();
    }
}

class CreateChannelDialog extends Component {
    static components = { Dialog };
    static props = ["close", "name?"];
    static template = "mail.CreateChannelDialog";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.orm = useService("orm");
        this.state = useState({ name: this.props.name || "", isInvalid: false });
    }

    /** @param {KeyboardEvent} ev */
    onKeydown(ev) {
        switch (ev.key) {
            case "Enter":
                this.onClickConfirm();
                break;
            default:
                this.state.isInvalid = false;
        }
    }

    async onClickConfirm() {
        const name = this.state.name.trim();
        if (!name) {
            this.state.isInvalid = true;
            return;
        }
        await makeNewChannel(name, this.store);
        this.props.close();
    }
}

class DiscussCommand extends Component {
    static components = { ImStatus };
    static template = "mail.DiscussCommand";
    static props = {
        counter: { type: Number, optional: true },
        executeCommand: Function,
        imgUrl: { String, optional: true },
        name: String,
        persona: { type: Object, optional: true },
        channel: { type: Object, optional: true },
        action: { type: Object, optional: true },
        searchValue: String,
        slots: Object,
    };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
    }
}

// -----------------------------------------------------------------------------
// add @ namespace + provider
// -----------------------------------------------------------------------------
commandSetupRegistry.add("@", {
    debounceDelay: 200,
    emptyMessage: _t("No conversation found"),
    name: _t("conversations"),
    placeholder: _t("Search a conversation"),
});

/**
 * @param {string} name
 * @param {import("models").Store} store
 */
async function makeNewChannel(name, store) {
    const { channel } = await store.fetchStoreData(
        "/discuss/create_channel",
        { name, group_id: store.internalUserGroupId },
        { readonly: false, requestData: true }
    );
    await channel.open({ focus: true, bypassCompact: true });
}

export class DiscussCommandPalette {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} env.services
     */
    constructor(env, options) {
        this.env = env;
        this.options = options;
        this.dialog = env.services.dialog;
        /** @type {import("models").Store} */
        this.store = env.services["mail.store"];
        this.orm = env.services.orm;
        this.suggestion = env.services["mail.suggestion"];
        this.ui = env.services.ui;
        this.commands = [];
        this.options = options;
        this.cleanedTerm = cleanTerm(this.options.searchValue);
    }

    async fetch() {
        await this.store.channels.fetch(); // FIXME: needed to search group chats without explicit name
        await this.store.searchConversations(this.cleanedTerm);
    }

    /** @param {Record[]} [filtered] persona or thread to filters, e.g. being build already in a category in a patch such as MENTIONS or RECENT */
    buildResults(filtered) {
        const TOTAL_LIMIT = this.ui.isSmall ? 7 : 10;
        const remaining = TOTAL_LIMIT - (filtered ? filtered.size : 0);
        let partners = [];
        if (this.store.self_partner) {
            partners = Object.values(this.store["res.partner"].records).filter(
                (partner) =>
                    partner.main_user_id?.share === false &&
                    cleanTerm(partner.displayName).includes(this.cleanedTerm) &&
                    (!filtered || !filtered.has(partner))
            );
            partners = this.suggestion
                .sortPartnerSuggestions(partners, this.cleanedTerm)
                .slice(0, TOTAL_LIMIT);
        }
        const selfPartner = this.store.self_partner?.in(partners)
            ? this.store.self_partner
            : undefined;
        if (selfPartner) {
            // selfPersona filtered here to put at the bottom as lowest priority
            partners = partners.filter((p) => p.notEq(selfPartner));
        }
        const channels = Object.values(this.store.Thread.records)
            .filter(
                (thread) =>
                    thread.channel_type &&
                    thread.channel_type !== "chat" &&
                    cleanTerm(thread.displayName).includes(this.cleanedTerm) &&
                    (!filtered || !filtered.has(thread))
            )
            .sort((c1, c2) => {
                if (c1.self_member_id && !c2.self_member_id) {
                    return -1;
                } else if (!c1.self_member_id && c2.self_member_id) {
                    return 1;
                }
                return c1.id - c2.id;
            })
            .slice(0, TOTAL_LIMIT);
        // balance remaining: half personas, half channels
        const elligiblePersonas = [];
        const elligibleChannels = [];
        let i = 0;
        while ((channels.length || partners.length) && i < remaining) {
            const p = partners.shift();
            const c = channels.shift();
            if (p) {
                elligiblePersonas.push(p);
                i++;
            }
            if (i >= remaining) {
                break;
            }
            if (c) {
                elligibleChannels.push(c);
                i++;
            }
        }
        for (const persona of elligiblePersonas) {
            this.commands.push(this.makeDiscussCommand(persona));
        }
        for (const channel of elligibleChannels) {
            this.commands.push(this.makeDiscussCommand(channel));
        }
        if (selfPartner && i < remaining) {
            // put self persona as lowest priority item
            this.commands.push(this.makeDiscussCommand(selfPartner));
        }
    }

    makeDiscussCommand(threadOrPersona, category) {
        if (threadOrPersona?.Model?.name === "Thread") {
            /** @type {import("models").Thread} */
            const thread = threadOrPersona;
            return {
                Component: DiscussCommand,
                action: async () => {
                    const channel = await this.store.Thread.getOrFetch(thread);
                    channel.open({ focus: true, bypassCompact: true });
                },
                name: thread.displayName,
                category,
                props: {
                    imgUrl: thread.parent_channel_id?.avatarUrl ?? thread.avatarUrl,
                    channel: thread.channel_type !== "chat" ? thread : undefined,
                    persona:
                        thread.channel_type === "chat" ? thread.correspondent.persona : undefined,
                    counter: thread.importantCounter,
                },
            };
        }
        if (threadOrPersona?.Model?._name === "res.partner") {
            /** @type {import("models").Persona} */
            const persona = threadOrPersona;
            const chat = persona.searchChat();
            return {
                Component: DiscussCommand,
                action: () => {
                    this.store.openChat({ partnerId: persona.id });
                },
                name: persona.displayName,
                category,
                props: {
                    imgUrl: persona.avatarUrl,
                    persona,
                    counter: chat ? chat.importantCounter : undefined,
                },
            };
        }
        if (threadOrPersona === NEW_CHANNEL) {
            return {
                Component: DiscussCommand,
                action: async () => {
                    const name = this.options.searchValue.trim();
                    if (name) {
                        await makeNewChannel(name, this.store);
                    } else {
                        this.dialog.add(CreateChannelDialog);
                    }
                },
                name: _t("Create Channel"),
                className: "o-mail-DiscussCommand-createChannel d-flex",
                props: { action: { icon: "fa fa-fw fa-hashtag", searchValueSuffix: true } },
            };
        }
        if (threadOrPersona === NEW_GROUP_CHAT) {
            const name = this.options.searchValue.trim();
            return {
                Component: DiscussCommand,
                action: () => {
                    this.dialog.add(CreateChatDialog, { name });
                },
                name: _t("Create Chat"),
                className: "d-flex",
                props: { action: { icon: "oi fa-fw oi-users" } },
            };
        }
        throw new Error(`Unsupported use of makeDiscussCommand("${threadOrPersona}")`);
    }
}

commandProviderRegistry.add("find_or_start_conversation", {
    namespace: "@",
    async provide(env, options) {
        const palette = new DiscussCommandPalette(env, options);
        await palette.fetch();
        palette.buildResults();
        palette.commands.slice(0, 8);
        if (!palette.store.inPublicPage) {
            palette.commands.push(palette.makeDiscussCommand(NEW_CHANNEL));
            palette.commands.push(palette.makeDiscussCommand(NEW_GROUP_CHAT));
        }
        return palette.commands;
    },
});
