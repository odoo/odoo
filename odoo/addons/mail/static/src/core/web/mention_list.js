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
            () => {
                if (!this.state.searchTerm) {
                    this.state.options = [];
                    return;
                }
                this.sequential(async () => {
                    await this.suggestionService.fetchSuggestions({
                        delimiter: this.props.type === "partner" ? "@" : "#",
                        term: this.state.searchTerm,
                    });
                    const suggestions = this.suggestionService.searchSuggestions(
                        {
                            delimiter: this.props.type === "partner" ? "@" : "#",
                            term: this.state.searchTerm,
                        },
                        { sort: true }
                    );
                    this.state.options = [
                        ...suggestions.mainSuggestions,
                        ...suggestions.extraSuggestions,
                    ];
                });
            },
            () => [this.state.searchTerm]
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
        markEventHandled(ev, "MentionList.onKeydown");
    }
}
