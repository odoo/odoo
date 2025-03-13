import { _t } from "@web/core/l10n/translation";
import { Component, useEffect, useState } from "@odoo/owl";
import { useService, useAutofocus } from "@web/core/utils/hooks";

import { NavigableList } from "@mail/core/common/navigable_list";
import { useSequential } from "@mail/utils/common/hooks";
import { useSuggestion } from "@mail/core/common/suggestion_hook";

export class MentionList extends Component {
    static template = "mail.MentionList";
    static components = { NavigableList };
    static props = {
        onSelect: { type: Function },
        close: { type: Function, optional: true },
        type: { type: String },
    };
    static defaultProps = {
        close: () => {},
    };

    setup() {
        super.setup();
        this.state = useState({
            options: [],
        });
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.suggestion = useSuggestion();
        this.sequential = useSequential();
        this.ref = useAutofocus({ mobile: true });

        useEffect(
            () => {
                if (!this.suggestion.state.term) {
                    this.state.options = [];
                    return;
                }
                this.sequential(async () => {
                    this.suggestion.search.delimiter = this.props.type === "partner" ? "@" : "#";
                    await this.suggestion.fetchSuggestions();
                    const { suggestions } = this.suggestion.searchSuggestions({ sort: true });
                    this.state.options = suggestions;
                });
            },
            () => [this.suggestion.state.term]
        );
    }

    get placeholder() {
        switch (this.props.type) {
            case "channel":
                return _t("Search for a channel...");
            case "partner":
                return _t("Search for a user...");
            default:
                return _t("Search...");
        }
    }

    get navigableListProps() {
        const props = {
            anchorRef: this.ref.el,
            position: "bottom-fit",
            isLoading: !!this.suggestion.state.term && this.suggestion.state.isFetching,
            onSelect: (...args) => {
                this.props.onSelect(...args);
                this.props.close();
            },
            options: [],
        };
        switch (this.props.type) {
            case "partner":
                this.state.options.forEach((option) => {
                    props.options.push({
                        label: option.name,
                        partner: option,
                    });
                });
                break;
            case "channel": {
                this.state.options.forEach((option) => {
                    props.options.push({
                        label: option.name,
                        channel: option,
                    });
                });
                break;
            }
        }
        return props;
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
