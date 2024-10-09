import { NavigableList } from "@mail/core/common/navigable_list";
import { cleanTerm } from "@mail/utils/common/format";
import { useSequential } from "@mail/utils/common/hooks";

import { Component, useEffect, useRef, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { CreateThreadDialog } from "./create_thread_dialog";
import { markEventHandled } from "@web/core/utils/misc";

export class SearchThread extends Component {
    static template = "mail.SearchThread";
    static props = [
        "autofocus?",
        "category?",
        "className?",
        "onCompleted?",
        "onSearchValueChanged?",
        "canCreate?",
    ];
    static defaultProps = { canCreate: true };
    static components = { NavigableList };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.ui = useState(useService("ui"));
        this.sequential = useSequential();
        this.discussCoreCommonService = useState(useService("discuss.core.common"));
        this.markEventHandled = markEventHandled;
        this.state = useState({
            searchValue: "",
            isFetching: false,
            focused: false,
        });
        this.searchBoxRef = useRef("searchBox");
        this.searchInputRef = useRef("searchInput");
        if (this.props.autofocus) {
            useAutofocus({ refName: "searchInput" });
        }
        useEffect(
            () => {
                this.props.onSearchValueChanged?.(this.state.searchValue);
                this.fetchSuggestions();
            },
            () => [this.state.searchValue]
        );
    }

    get inputPlaceholder() {
        if (!this.props.category) {
            return _t("Find or start a conversation");
        } else {
            return this.props.category.addTitle;
        }
    }

    async fetchSuggestions() {
        const cleanedTerm = cleanTerm(this.state.searchValue);
        if (!cleanedTerm) {
            return;
        }
        const data = await this.sequential(async () => {
            this.state.isFetching = true;
            const data = await rpc("/discuss/search", {
                term: cleanedTerm,
                category_id: this.props.category?.id,
            });
            this.state.isFetching = false;
            return data;
        });
        this.store.insert(data);
    }

    get suggestions() {
        const cleanedTerm = cleanTerm(this.state.searchValue);
        const suggestions = [];
        if (!cleanedTerm) {
            return suggestions;
        }
        if (!this.props.category || this.props.category === this.store.discuss.chats) {
            suggestions.push(
                ...Object.values(this.store.Thread.records)
                    .filter(
                        (thread) =>
                            thread.channel_type === "group" &&
                            cleanTerm(thread.displayName).includes(cleanedTerm)
                    )
                    .map((thread) => {
                        return {
                            buttonClass: "text-reset",
                            optionTemplate: "discuss.SearchThread.channel",
                            classList: "o-mail-SearchThread-suggestion",
                            channel: thread,
                            group: 5,
                        };
                    })
            );
            suggestions.push(
                ...Object.values(this.store.Persona.records)
                    .filter(
                        (persona) =>
                            persona !== this.store.self &&
                            persona.isInternalUser &&
                            cleanTerm(persona.name).includes(cleanedTerm)
                    )
                    .map((persona) => {
                        return {
                            buttonClass: "text-reset",
                            optionTemplate: "discuss.SearchThread.partner",
                            classList: "o-mail-SearchThread-suggestion",
                            partner: persona,
                            group: 10,
                        };
                    })
            );
        }
        if (!this.props.category || this.props.category === this.store.discuss.channels) {
            suggestions.push(
                ...Object.values(this.store.Thread.records)
                    .filter(
                        (thread) =>
                            !thread.parent_channel_id &&
                            thread.channel_type === "channel" &&
                            cleanTerm(thread.name).includes(cleanedTerm)
                    )
                    .map((thread) => {
                        return {
                            buttonClass: "text-reset",
                            optionTemplate: "discuss.SearchThread.channel",
                            classList: "o-mail-SearchThread-suggestion",
                            channel: thread,
                            group: 90,
                        };
                    })
            );
        }
        return suggestions;
    }

    get navigableListProps() {
        const props = {
            anchorRef: this.searchBoxRef?.el,
            position: "bottom-fit",
            onSelect: (ev, option) => this.onSelect(option),
            options: [],
            isLoading: this.state.isFetching,
            groupSeparators: false,
        };
        const create = [
            this.props.category === this.store.discuss.channels ? "channel" : undefined,
            this.props.category === this.store.discuss.chats ? "group" : undefined,
        ].filter((type) => !!type);
        const createOption = {
            create,
            optionTemplate:
                create.length !== 1
                    ? "discuss.SearchThread.new"
                    : create[0] === "channel"
                    ? "discuss.SearchThread.newChannel"
                    : create[0] === "group"
                    ? "discuss.SearchThread.newGroup"
                    : "discuss.SearchThread.new",
            classList: "o-mail-SearchThread-suggestion py-1",
            label: this.state.searchValue,
            group: 100,
        };
        if (!this.state.searchValue) {
            if (this.canCreate && this.state.focused) {
                props.options.push(createOption);
            }
            return props;
        }
        props.options = this.suggestions.slice(0, 8);
        if (this.canCreate) {
            props.options.push(createOption);
        }
        if (!props.options.length && !this.state.isFetching) {
            props.options.push({
                classList: "o-mail-SearchThread-suggestion",
                label: _t("No results found"),
                unselectable: true,
            });
        }
        return props;
    }

    get canCreate() {
        return (
            this.props.canCreate &&
            (!this.props.category ||
                this.props.category === this.store.discuss.channels ||
                this.props.category === this.store.discuss.chats)
        );
    }

    async onSelect(option) {
        if (option.create) {
            const threadTypes = option.create.filter((type) => !!type);
            this.env.services.dialog.add(CreateThreadDialog, {
                name: this.state.searchValue,
                types: threadTypes.length > 0 ? threadTypes : undefined,
                onCompleted: this.onCompleted.bind(this),
            });
            return;
        } else if (option.channel?.channel_type === "group") {
            const channel = await this.store.Thread.getOrFetch(option.channel);
            channel.open();
        } else if (option.channel) {
            this.store.joinChannel(option.channel.id, option.channel.name);
        } else if (option.partner) {
            this.discussCoreCommonService.startChat([option.partner.id]);
        }
        this.onCompleted();
    }

    onCompleted() {
        this.state.searchValue = "";
        this.props.onCompleted?.();
    }

    onFocusin() {
        this.state.focused = true;
    }

    onFocusout() {
        this.state.focused = false;
    }
}
