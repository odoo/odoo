import { cleanTerm } from "@mail/utils/common/format";
import { useState } from "@web/owl2/utils";

import { Component } from "@odoo/owl";

import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { highlightText } from "@web/core/utils/html";

const commandSetupRegistry = registry.category("command_setup");
const commandProviderRegistry = registry.category("command_provider");

const NEW_CHANNEL = "NEW_CHANNEL";
const VIEW_HIDDEN = "VIEW_HIDDEN";

class CreateChannelDialog extends Component {
    static components = { Dialog };
    static props = ["close", "name?"];
    static template = "mail.CreateChannelDialog";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.orm = useService("orm");
        this.state = useState({
            name: this.props.name || "",
            isInvalid: false,
            is_readonly: false,
        });
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
        await makeNewChannel(name, this.store, this.state.is_readonly);
        this.props.close();
    }
}

export class DiscussCommand extends Component {
    static components = { DiscussAvatar };
    static template = "mail.DiscussCommand";
    static props = {
        counter: { type: Number, optional: true },
        executeCommand: Function,
        imgUrl: { type: String, optional: true },
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

    get formattedEmail() {
        return highlightText(this.props.searchValue, this.email, "fw-bolder text-primary");
    }

    get email() {
        return this.props.persona?.email;
    }
}

// -----------------------------------------------------------------------------
// add @ namespace + provider
// -----------------------------------------------------------------------------
commandSetupRegistry.add("@", {
    debounceDelay: 200,
    emptyMessage: _t("No conversation found"),
    name: _t("conversations"),
    placeholder: _t("Search conversations"),
});

/**
 * @param {string} name
 * @param {import("models").Store} store
 */
async function makeNewChannel(name, store, is_readonly = false) {
    const { channel } = await store.fetchStoreData(
        "/discuss/create_channel",
        { name, group_id: store.internalUserGroupId, is_readonly },
        { readonly: false, requestData: true }
    );
    channel.open({ focus: true, bypassCompact: true });
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
        if (this.store.self_user?.share === false) {
            partners = Object.values(this.store["res.partner"].records).filter(
                (partner) =>
                    partner.main_user_id?.share === false &&
                    (cleanTerm(partner.displayName).includes(this.cleanedTerm) ||
                        cleanTerm(partner.email).includes(this.cleanedTerm)) &&
                    (!filtered || !filtered.has(partner))
            );
            partners = this.suggestion
                .sortPartnerSuggestions(partners, this.cleanedTerm)
                .slice(0, TOTAL_LIMIT);
        }
        const selfPartner = this.store.self_user?.partner_id?.in(partners)
            ? this.store.self_user.partner_id
            : undefined;
        if (selfPartner) {
            // selfPersona filtered here to put at the bottom as lowest priority
            partners = partners.filter((p) => p.notEq(selfPartner));
        }
        const channels = Object.values(this.store["discuss.channel"].records)
            .filter(
                (channel) =>
                    channel.channel_type &&
                    channel.channel_type !== "chat" &&
                    cleanTerm(channel.displayName).includes(this.cleanedTerm) &&
                    (!filtered || !filtered.has(channel))
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

    makeDiscussCommand(channelOrPersona, category) {
        if (channelOrPersona?.Model?.getName() === "discuss.channel") {
            /** @type {import("models").DiscussChannel} */
            const channel = channelOrPersona;
            return {
                Component: DiscussCommand,
                action: async () => {
                    const channelToOpen = await this.store["discuss.channel"].getOrFetch(
                        channel.id
                    );
                    channelToOpen.open({ focus: true, bypassCompact: true });
                },
                name: channel.displayName,
                category,
                props: {
                    imgUrl: channel.parent_channel_id?.avatarUrl ?? channel.avatarUrl,
                    channel: channel.channel_type !== "chat" ? channel : undefined,
                    persona:
                        channel.channel_type === "chat" ? channel.correspondent.persona : undefined,
                    counter: channel.importantCounter,
                },
            };
        }
        if (channelOrPersona?.Model?.getName() === "res.partner") {
            /** @type {import("models").Persona} */
            const persona = channelOrPersona;
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
        if (channelOrPersona === NEW_CHANNEL) {
            return {
                Component: DiscussCommand,
                action: () => {
                    this.dialog.add(CreateChannelDialog, {
                        name: this.options.searchValue?.trim(),
                    });
                },
                name: _t("Create Channel"),
                className: "o-mail-DiscussCommand-createChannel d-flex",
                props: { action: { icon: "fa fa-fw fa-hashtag", searchValueSuffix: true } },
            };
        }
        if (channelOrPersona === VIEW_HIDDEN) {
            return {
                Component: DiscussCommand,
                name: _t("View hidden conversations"),
                props: { action: {} },
                action: () => {
                    this.env.services.action.doAction("mail.discuss_my_conversations_action");
                },
            };
        }
        throw new Error(`Unsupported use of makeDiscussCommand("${channelOrPersona}")`);
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
            if (palette.cleanedTerm) {
                palette.commands.push(palette.makeDiscussCommand(NEW_CHANNEL));
            }
            if (palette.store.has_unpinned_channels) {
                palette.commands.push(palette.makeDiscussCommand(VIEW_HIDDEN));
            }
        }
        return palette.commands;
    },
});
