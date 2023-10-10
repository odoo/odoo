/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component, useEffect, useState } from "@odoo/owl";
import { NavigableList } from "@mail/core/common/navigable_list";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { useSequential } from "@mail/utils/common/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").Composer} composer
 * @extends {Component<Props, Env>}
 */
export class CannedResponseList extends Component {
    static template = "mail.canned_response_list";
    static components = { NavigableList };
    static props = ["composer", "close?"];
    static defaultProps = {};

    setup() {
        this.ref = useAutofocus({ mobile: true });
        this.suggestionService = useService("mail.suggestion");
        this.sequential = useSequential();
        this.state = useState({
            searchTerm: "",
            options: [],
        });

        useEffect(
            () => {
                this.state.options = this.suggestionService.searchCannedResponseSuggestions(
                    this.state.searchTerm,
                    true
                ).mainSuggestions;
            },
            () => [this.state.searchTerm]
        );
    }

    get navigableListProps() {
        const props = {
            anchorRef: this.ref.el,
            position: "top-fit",
            placeholder: _t("Loading"),
            onSelect: (ev, option) => {
                this.props.composer.insertText(option.label);
                this.props.composer.thread.showCannedResponse = false;
            },
            optionTemplate: "mail.Composer.suggestionCannedResponse",
            options: this.state.options.map((suggestion) => ({
                cannedResponse: suggestion,
                name: suggestion.name,
                label: suggestion.substitution,
                classList: "o-mail-Composer-suggestion",
            })),
        };
        return props;
    }
}
