/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component, useEffect, useState } from "@odoo/owl";
import { useService, useAutofocus } from "@web/core/utils/hooks";

import { NavigableList } from "@mail/core/common/navigable_list";
import { useSequential } from "@mail/utils/common/hooks";
import { markEventHandled } from "@web/core/utils/misc";

export class MentionList extends Component {
    static template = "mail.MentionList";
    static components = { NavigableList };
    static props = {
        onSelect: { type: Function },
        close: { type: Function, optional: true },
        thread: { optional: true },
        type: { type: String },
    };
    setup() {
        this.state = useState({
            searchTerm: "",
            options: [],
        });
        this.orm = useService("orm");
        this.store = useState(useService("mail.store"));
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
                    await this.suggestionService.fetchSuggestions({ delimiter, term }, { thread });
                    const suggestions = this.suggestionService.searchSuggestions(
                        { delimiter, term },
                        { sort: true, thread }
                    );
                    this.state.options = [
                        ...suggestions.mainSuggestions,
                        ...suggestions.extraSuggestions,
                    ];
                });
            },
            () => [
                this.state.searchTerm,
                this.props.type === "partner" ? "@" : "#",
                this.props.thread,
            ]
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
            placeholder: _t("Loading"),
            onSelect: this.props.onSelect,
            options: [],
        };
        switch (this.props.type) {
            case "partner":
                props.optionTemplate = "mail.Composer.suggestionPartner";
                props.options = this.state.options.map((suggestion) => {
                    return {
                        label: suggestion.name,
                        partner: suggestion,
                        classList: "o-mail-Composer-suggestion",
                    };
                });
                break;
            case "channel":
                props.optionTemplate = "mail.Composer.suggestionThread";
                props.options = this.state.options.map((suggestion) => {
                    return {
                        label: suggestion.displayName,
                        thread: suggestion,
                        classList: "o-mail-Composer-suggestion",
                    };
                });
                break;
        }
        return props;
    }

    onKeydown(ev) {
        markEventHandled(ev, "MentionList.onKeydown");
    }
}
