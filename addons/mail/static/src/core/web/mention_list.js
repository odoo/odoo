import { _t } from "@web/core/l10n/translation";
import { Component, signal, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

import { NavigableList } from "@mail/core/common/navigable_list";
import { SearchInput } from "@mail/core/common/search_input";
import {
    mapSuggestionsToOptions,
    onSelectType,
    SUGGESTION_DELIMITERS,
} from "@mail/core/common/suggestion_hook";
import { propComputed, useSearch } from "@mail/utils/common/hooks";

export class MentionList extends Component {
    static template = "mail.MentionList";
    static components = { NavigableList, SearchInput };

    setup() {
        super.setup();
        this.onSelectSuggestion = this.onSelectSuggestion.bind(this);
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.onSelect = useProps.static("onSelect", onSelectType(this.store));
        this.close = useProps.static(
            "close",
            t.function([]).optional(() => {})
        );
        this.composerType = propComputed("composerType", t.string());
        this.thread = propComputed("thread", t.instanceOf(this.store["mail.thread"]).optional());
        this.type = propComputed("type", t.string());
        this.suggestionService = useService("mail.suggestion");
        this.anchorRef = signal.ref();
        this.search = useSearch({
            fetch: (term) =>
                this.suggestionService.fetchSuggestions(
                    { delimiter: this.delimiter, term },
                    { composerType: this.composerType(), thread: this.thread() }
                ),
            filter: (term) =>
                this.suggestionService.searchSuggestions(
                    { delimiter: this.delimiter, term },
                    { composerType: this.composerType(), thread: this.thread() }
                ).suggestions,
            deps: () => [this.delimiter, this.thread()],
        });
    }

    get delimiter() {
        return SUGGESTION_DELIMITERS.PARTNER;
    }

    get placeholder() {
        switch (this.type()) {
            case "Partner":
                return _t("Search for a user...");
            default:
                return _t("Search...");
        }
    }

    /** @type {ReturnType<typeof import("@mail/core/common/suggestion_hook").onSelectType>["type"]} */
    onSelectSuggestion(...args) {
        this.onSelect(...args);
        this.close?.();
    }

    get navigableListProps() {
        return {
            anchorRef: this.anchorRef,
            position: "bottom-fit",
            isLoading: !!this.search.searchTerm && this.search.loading,
            onSelect: this.onSelectSuggestion,
            ...mapSuggestionsToOptions(this.type(), this.search.results, {
                thread: this.thread(),
            }),
        };
    }

    onKeydown(ev) {
        switch (ev.key) {
            case "Escape": {
                this.close?.();
                break;
            }
        }
    }
}
