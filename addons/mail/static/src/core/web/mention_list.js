import { _t } from "@web/core/l10n/translation";
import { Component, props, signal, t } from "@odoo/owl";
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
        this.props = props({
            close: t.function([]).optional(() => {}),
            composerType: t.string(),
            onSelect: t.function([t.instanceOf(Event), optionType(this.store), t.record()]),
            thread: t.instanceOf(this.store["mail.thread"].Class).optional(),
            type: t.string(),
        });
        this.suggestionService = useService("mail.suggestion");
        this.anchorRef = signal.ref();
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
            anchorRef: this.anchorRef,
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
