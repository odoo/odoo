/* @odoo-module */

import { useStore } from "@mail/core/common/messaging_hook";
import { NavigableList } from "@mail/core/common/navigable_list";
import { useDiscussCoreCommon } from "@mail/discuss/core/common/discuss_core_common_service";
import { cleanTerm } from "@mail/utils/common/format";
import { createLocalId } from "@mail/utils/common/misc";

import { Component, onMounted, useEffect, useRef, useState } from "@odoo/owl";

import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { _t } from "@web/core/l10n/translation";
import { TagsList } from "@web/core/tags_list/tags_list";
import { useService } from "@web/core/utils/hooks";
import { isEventHandled, markEventHandled } from "@web/core/utils/misc";
import { useSequential } from "@mail/utils/common/hooks";

export class ChannelSelector extends Component {
    static components = { TagsList, NavigableList };
    static props = ["category", "onValidate?", "autofocus?", "multiple?"];
    static defaultProps = { multiple: true };
    static template = "discuss.ChannelSelector";

    setup() {
        this.discussCoreCommonService = useDiscussCoreCommon();
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = useStore();
        /** @type {import("@mail/core/common/thread_service").ThreadService} */
        this.threadService = useState(useService("mail.thread"));
        this.personaService = useService("mail.persona");
        /** @type {import("@mail/core/common/suggestion_service").SuggestionService} */
        this.suggestionService = useService("mail.suggestion");
        this.orm = useService("orm");
        this.sequential = useSequential();
        this.state = useState({
            value: "",
            selectedPartners: [],
            navigableListProps: {
                anchorRef: undefined,
                position: "bottom-fit",
                onSelect: (ev, option) => this.onSelect(option),
                placeholder: _t("Loading"),
                optionTemplate:
                    this.props.category.id === "channels"
                        ? "discuss.ChannelSelector.channel"
                        : "discuss.ChannelSelector.chat",
                options: [],
                isLoading: false,
            },
        });
        this.inputRef = useRef("input");
        this.rootRef = useRef("root");
        if (this.props.autofocus) {
            onMounted(() => this.inputRef.el.focus());
        }
        this.markEventHandled = markEventHandled;
        useEffect(
            () => {
                this.state.navigableListProps.anchorRef = this.rootRef?.el;
                this.state.navigableListProps.optionTemplate =
                    this.props.category.id === "channels"
                        ? "discuss.ChannelSelector.channel"
                        : "discuss.ChannelSelector.chat";
            },
            () => [this.rootRef, this.props.category]
        );
        useEffect(
            () => {
                this.state.navigableListProps.isLoading = true;
                this.fetchSuggestions().then(
                    () => (this.state.navigableListProps.isLoading = false)
                );
            },
            () => [this.state.value]
        );
    }

    async fetchSuggestions() {
        const cleanedTerm = cleanTerm(this.state.value);
        if (cleanedTerm) {
            if (this.props.category.id === "channels") {
                const domain = [
                    ["channel_type", "=", "channel"],
                    ["name", "ilike", cleanedTerm],
                ];
                const fields = ["name"];
                const results = await this.sequential(() =>
                    this.orm.searchRead("discuss.channel", domain, fields, {
                        limit: 10,
                    })
                );
                if (!results) {
                    this.state.navigableListProps.options = [];
                    return;
                }
                const choices = results.map((channel) => {
                    return {
                        channelId: channel.id,
                        classList: "o-discuss-ChannelSelector-suggestion",
                        label: channel.name,
                    };
                });
                choices.push({
                    channelId: "__create__",
                    classList: "o-discuss-ChannelSelector-suggestion",
                    label: cleanedTerm,
                });
                this.state.navigableListProps.options = choices;
                return;
            }
            if (this.props.category.id === "chats") {
                const results = await this.sequential(() =>
                    this.orm.call("res.partner", "im_search", [
                        cleanedTerm,
                        10,
                        this.state.selectedPartners,
                    ])
                );
                if (!results) {
                    this.state.navigableListProps.options = [];
                    return;
                }
                const suggestions = this.suggestionService
                    .sortPartnerSuggestions(results, cleanedTerm)
                    .map((data) => {
                        this.personaService.insert({ ...data, type: "partner" });
                        return {
                            classList: "o-discuss-ChannelSelector-suggestion",
                            label: data.name,
                            partner: data,
                        };
                    });
                if (this.store.self.name.includes(cleanedTerm)) {
                    suggestions.push({
                        classList: "o-discuss-ChannelSelector-suggestion",
                        label: this.store.self.name,
                        partner: this.store.self,
                    });
                }
                if (suggestions.length === 0) {
                    suggestions.push({
                        classList: "o-discuss-ChannelSelector-suggestion",
                        label: _t("No results found"),
                        unselectable: true,
                    });
                }
                this.state.navigableListProps.options = suggestions;
                return;
            }
        }
        this.state.navigableListProps.options = [];
        return;
    }

    onSelect(option) {
        if (this.props.category.id === "channels") {
            if (option.channelId === "__create__") {
                this.env.services.orm
                    .call("discuss.channel", "channel_create", [
                        option.label,
                        this.store.internalUserGroupId,
                    ])
                    .then((data) => {
                        const channel = this.discussCoreCommonService.createChannelThread(data);
                        this.threadService.sortChannels();
                        this.threadService.open(channel);
                    });
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
            const selectedPartnerIds = this.state.selectedPartners;
            if (selectedPartnerIds.length === 0) {
                return;
            }
            await this.discussCoreCommonService.startChat(
                selectedPartnerIds,
                this.env.inChatWindow
            );
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
}
