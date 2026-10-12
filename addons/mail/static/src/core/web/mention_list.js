import { _t } from "@web/core/l10n/translation";
import { Component, t, useListener, useProps } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";

import { NavigableList } from "@mail/core/common/navigable_list";
import { SearchInput } from "@mail/core/common/search_input";
import {
    mapSuggestionsToOptions,
    optionType,
    SUGGESTION_DELIMITERS,
} from "@mail/core/common/suggestion_hook";
import { useSearch } from "@mail/utils/common/hooks";

export class MentionList extends Component {
    static template = "mail.MentionList";
    static components = { NavigableList, SearchInput };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.props = useProps({
            close: t.function([]).optional(() => {}),
            composerType: t.string(),
            onSelect: t.function([t.instanceOf(Event), optionType(this.store)]),
            thread: t.instanceOf(this.store["mail.thread"]).optional(),
            type: t.string(),
        });
        this.suggestionService = useService("mail.suggestion");
        this.isMobileOS = isMobileOS();
        useListener(window, "keydown", (ev) => this.onKeydown(ev), true);
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
        return SUGGESTION_DELIMITERS.PARTNER;
    }

    get placeholder() {
        switch (this.props.type) {
            case "Partner":
                return _t("Search for a user...");
            default:
                return _t("Search...");
        }
    }

    get navigableListProps() {
        return {
            closeOnSelect: false, // a click on the search input must not close the list alone
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
                ev.stopPropagation();
                this.props.close();
                break;
            }
        }
    }
}
