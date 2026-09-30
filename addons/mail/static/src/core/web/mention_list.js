import { _t } from "@web/core/l10n/translation";
import { Component, useEffect, useState } from "@odoo/owl";
import { useService, useAutofocus } from "@web/core/utils/hooks";

import { NavigableList } from "@mail/core/common/navigable_list";
import { mapSuggestionsToOptions } from "@mail/core/common/suggestion_hook";
import { useSequential } from "@mail/utils/common/hooks";

export class MentionList extends Component {
    static template = "mail.MentionList";
    static components = { NavigableList };
    static props = {
        onSelect: { type: Function },
        close: { type: Function, optional: true },
        thread: { optional: true },
        type: { type: String },
    };
    static defaultProps = {
        close: () => {},
    };

    setup() {
        super.setup();
        this.state = useState({
            searchTerm: "",
            options: [],
            isFetching: false,
        });
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.suggestionService = useService("mail.suggestion");
        this.sequential = useSequential();
        this.ref = useAutofocus({ mobile: true });

        useEffect(
            (term, delimiter, thread) => {
                if (!term) {
                    this.state.options = [];
                    return;
                }
                this.sequential(async () => {
                    this.state.isFetching = true;
                    try {
                        await this.suggestionService.fetchSuggestions(
                            { delimiter, term },
                            { thread }
                        );
                    } finally {
                        this.state.isFetching = false;
                    }
                    const { suggestions } = this.suggestionService.searchSuggestions(
                        { delimiter, term },
                        { thread }
                    );
                    this.state.options = suggestions;
                });
            },
            () => [
                this.state.searchTerm,
                this.props.type === "Partner" ? "@" : "#",
                this.props.thread,
            ]
        );
    }

    get placeholder() {
        switch (this.props.type) {
            case "Thread":
                return _t("Search for a channel...");
            case "Partner":
                return _t("Search for a user...");
            default:
                return _t("Search...");
        }
    }

    get navigableListProps() {
        return {
            anchorRef: this.ref.el,
            position: "bottom-fit",
            isLoading: !!this.state.searchTerm && this.state.isFetching,
            onSelect: (...args) => {
                this.props.onSelect(...args);
                this.props.close();
            },
            ...mapSuggestionsToOptions(this.props.type, this.state.options, {
                thread: this.props.thread,
            }),
        };
    }

    onKeydown(ev) {
        switch (ev.key) {
            case "Escape": {
                this.props.close();
                break;
            }
        }
    }
}
