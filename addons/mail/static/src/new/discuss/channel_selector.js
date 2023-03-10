/* @odoo-module */

import { useStore } from "../core/messaging_hook";
import { TagsList } from "@web/views/fields/many2many_tags/tags_list";
import { NavigableList } from "../composer/navigable_list";
import { useService } from "@web/core/utils/hooks";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { cleanTerm } from "@mail/new/utils/format";
import { createLocalId, isEventHandled } from "@mail/new/utils/misc";
import { _t } from "@web/core/l10n/translation";

export class ChannelSelector extends Component {
    static components = { TagsList, NavigableList };
    static props = ["category", "onValidate?", "autofocus?", "multiple?"];
    static defaultProps = { multiple: true };
    static template = "mail.ChannelSelector";

    setup() {
        this.store = useStore();
        this.threadService = useState(useService("mail.thread"));
        this.personaService = useService("mail.persona");
        this.orm = useService("orm");
        this.state = useState({
            value: "",
            selectedPartners: [],
        });
        this.inputRef = useRef("input");
        this.rootRef = useRef("root");
        if (this.props.autofocus) {
            onMounted(() => this.inputRef.el.focus());
        }
    }

    async fetchSuggestions(term) {
        const cleanedTerm = cleanTerm(term);
        if (cleanedTerm) {
            if (this.props.category.id === "channels") {
                const domain = [
                    ["channel_type", "=", "channel"],
                    ["name", "ilike", cleanedTerm],
                ];
                const fields = ["name"];
                const results = await this.orm.searchRead("mail.channel", domain, fields, {
                    limit: 10,
                });
                const choices = results.map((channel) => {
                    return {
                        channelId: channel.id,
                        classList: "o-ChannelSelector-suggestion",
                        label: channel.name,
                    };
                });
                choices.push({
                    channelId: "__create__",
                    classList: "o-ChannelSelector-suggestion",
                    label: cleanedTerm,
                });
                return choices;
            }
            if (this.props.category.id === "chats") {
                const results = await this.orm.call("res.partner", "im_search", [
                    cleanedTerm,
                    10,
                    this.state.selectedPartners,
                ]);
                const suggestions = results.map((data) => {
                    this.personaService.insert({ ...data, type: "partner" });
                    return {
                        classList: "o-ChannelSelector-suggestion",
                        label: data.name,
                        partner: data,
                    };
                });
                if (this.store.self.name.includes(cleanedTerm)) {
                    suggestions.push({
                        classList: "o-ChannelSelector-suggestion",
                        label: this.store.self.name,
                        partner: this.store.self,
                    });
                }
                return suggestions;
            }
        }
        return [];
    }

    onSelect(option) {
        if (this.props.category.id === "channels") {
            if (option.channelId === "__create__") {
                this.threadService.createChannel(option.label);
            } else {
                this.threadService.joinChannel(option.channelId, option.label);
            }
            this.onValidate();
        }
        if (this.props.category.id === "chats") {
            if (!this.state.selectedPartners.includes(option.partner.id)) {
                this.state.selectedPartners.push(option.partner.id);
            }
            this.state.value = "";
        }
        if (!this.props.multiple) {
            this.onValidate();
        }
    }

    async onValidate() {
        if (this.props.category.id === "chats") {
            const selectedPartners = this.state.selectedPartners;
            if (selectedPartners.length === 0) {
                return;
            }
            if (selectedPartners.length === 1) {
                await this.threadService
                    .joinChat(selectedPartners[0])
                    .then((chat) => this.threadService.open(chat, this.env.inChatWindow));
            } else {
                const partners_to = [...new Set([this.store.self.id, ...selectedPartners])];
                await this.threadService.createGroupChat({ partners_to });
            }
        }
        if (this.props.onValidate) {
            this.props.onValidate();
        }
    }

    onKeydownInput(ev) {
        const hotkey = getActiveHotkey(ev);
        switch (hotkey) {
            case "enter":
                if (isEventHandled(ev, "NavigableList.select") || !this.state.value === "") {
                    return;
                }
                this.onValidate();
                break;
            case "backspace":
                if (this.state.selectedPartners.length > 0 && this.state.value === "") {
                    this.state.selectedPartners.pop();
                }
                return;
            default:
                return;
        }
        ev.stopPropagation();
        ev.preventDefault();
    }

    removeFromSelectedPartners(id) {
        this.state.selectedPartners = this.state.selectedPartners.filter(
            (partnerId) => partnerId !== id
        );
        this.inputRef.el.focus();
    }

    get inputPlaceholder() {
        return this.state.selectedPartners.length > 0
            ? _t("Press Enter to start")
            : this.props.category.addTitle;
    }

    get tagsList() {
        const res = [];
        for (const partnerId of this.state.selectedPartners) {
            const partner = this.store.personas[createLocalId("partner", partnerId)];
            res.push({
                id: partner.id,
                text: partner.name,
                className: "m-1 py-1",
                colorIndex: Math.floor(partner.name.length % 10),
                onDelete: () => this.removeFromSelectedPartners(partnerId),
            });
        }
        return res;
    }

    get navigableListProps() {
        return {
            anchorRef: this.rootRef.el,
            position: "bottom",
            onSelect: (ev, option) => this.onSelect(option),
            sources: [
                {
                    placeholder: "Loading",
                    optionTemplate:
                        this.props.category.id === "channels"
                            ? "mail.ChannelSelector.channel"
                            : "mail.ChannelSelector.chat",
                    options: this.fetchSuggestions(this.state.value),
                },
            ],
        };
    }
}
