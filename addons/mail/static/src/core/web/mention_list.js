import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { useChildRef, useService } from "@web/core/utils/hooks";

import { NavigableList } from "@mail/core/common/navigable_list";
import { SearchInput } from "@mail/core/common/search_input";
import { mapSuggestionsToOptions } from "@mail/core/common/suggestion_hook";
import { useSearch } from "@mail/utils/common/hooks";

export class MentionList extends Component {
    static template = "mail.MentionList";
    static components = { NavigableList, SearchInput };
    static props = {
        onSelect: { type: Function },
        close: { type: Function, optional: true },
        composerType: { type: String },
        thread: { optional: true },
        type: { type: String },
    };
    static defaultProps = {
        close: () => {},
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.suggestionService = useService("mail.suggestion");
        this.ref = useChildRef();
        this.search = useSearch({
            fetch: (term) =>
                this.suggestionService.fetchSuggestions(
                    { delimiter: this.delimiter, term },
                    { composerType: this.props.composerType, thread: this.props.thread }
                ),
            filter: (term) =>
                this.suggestionService.searchSuggestions(
                    { delimiter: this.delimiter, term },
                    { composerType: this.props.composerType, thread: this.props.thread }
                ).suggestions,
            deps: () => [this.delimiter, this.props.thread],
        });
    }

    get delimiter() {
        return this.props.type === "Partner" ? "@" : "#";
    }

    get placeholder() {
        switch (this.props.type) {
            case "discuss.channel":
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
            isLoading: !!this.search.searchTerm && this.search.loading,
            onSelect: (...args) => {
                this.props.onSelect(...args);
                this.props.close();
            },
            ...mapSuggestionsToOptions(this.props.type, this.search.results, {
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
