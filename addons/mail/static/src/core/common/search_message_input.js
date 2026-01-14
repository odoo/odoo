import { Component, useExternalListener, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useAutofocus, useBus } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { SearchModel } from "@web/search/search_model";
import { WithSearch } from "@web/search/with_search/with_search";

/**
 * @typedef {Object} SearchFilter
 * @property {string} label
 * @property {string} name
 * @property {true|false|undefined} [is_notification]
 */

/**
 * @typedef {Object} Props
 * @property {ReturnType<typeof import("@mail/core/common/message_search_hook").useMessageSearch>} messageSearch
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {function} [closeSearch]
 * @extends {Component<Props, Env>}
 */
export class SearchMessageInputWithSearch extends Component {
    static template = "mail.SearchMessageInputWithSearch";
    static props = ["closeSearch?", "messageSearch", "thread"];
    static components = { SearchBar };

    setup() {
        super.setup();
        this.state = useState({ searchDomain: "" });
        this.searchBarToggler = useSearchBarToggler();
        useAutofocus();
        useExternalListener(
            browser,
            "keydown",
            (ev) => {
                if (ev.key === "Escape") {
                    this.props.closeSearch?.();
                }
            },
            { capture: true }
        );
        useBus(this.env.searchModel, "update", this.search);
    }

    search() {
        this.props.messageSearch.searchDomain = this.env.searchModel.domain;
        if (this.env.searchModel.domain.length == 0) {
            return this.props.messageSearch.clear();
        }
        this.props.messageSearch.search();
    }

    clear() {
        this.state.searchDomain = [];
        this.props.messageSearch.clear();
        this.props.closeSearch?.();
    }
}

export class MailMessageSearchModel extends SearchModel {
    async load(config) {
        await super.load(config);
        const trackedFields = Object.values(config.searchViewFields).filter((f) =>
            f.name.startsWith("tracking.")
        );
        this.searchItems = {};
        this._createGroupOfSearchItems([
            {
                description: "Full Search",
                fieldName: "full_search",
                fieldType: "text",
                type: "field",
            },
            {
                description: "Author",
                fieldName: "author_id",
                fieldType: "many2one",
                relation: "res.partner",
                type: "field",
            },
        ]);
        this._createGroupOfSearchItems(
            trackedFields.map((f) => ({
                description: f.string,
                fieldName: f.name,
                fieldType: f.type,
                type: "field",
            }))
        );
        this._createGroupOfSearchItems([
            {
                description: _t("Conversations"),
                domain: "[('tracking', '=', False)]",
                groupNumber: 100,
                name: "conversations",
                type: "filter",
            },
            {
                description: _t("Tracked Changes"),
                domain: "[('tracking', '!=', False)]",
                groupNumber: 100,
                name: "tracked_changes",
                type: "filter",
            },
        ]);
        this._createGroupOfSearchItems(
            trackedFields.map((f) => ({
                description: f.string,
                domain: `[('${f.name}', '!=', False)]`,
                groupNumber: 1000,
                type: "filter",
            }))
        );
    }
}

export class SearchMessageInput extends Component {
    static template = "mail.SearchMessageInput";
    static components = { WithSearch, SearchMessageInputWithSearch };
    static props = ["closeSearch?", "messageSearch", "thread"];

    get withSearchProps() {
        const config = this.env.model?.config;
        const searchViewFields = {
            full_search: {
                name: "full_search",
                searchable: true,
                type: "text",
                string: "Full Search",
            },
            author_id: {
                name: "author_id",
                searchable: true,
                type: "many2one",
                relation: "res.partner",
                string: "Author",
            },
        };
        if (!config) {
            return {
                resModel: "mail.message",
                SearchModel: MailMessageSearchModel,
                searchMenuTypes: [],
                searchViewFields: searchViewFields,
            };
        }
        Object.values(config.fields)
            .filter((f) => f.tracking)
            .forEach((f) => {
                const fname = `tracking.${config.resModel},${f.name}`;
                searchViewFields[fname] = {
                    ...f,
                    name: fname,
                };
            });
        return {
            resModel: "mail.message",
            SearchModel: MailMessageSearchModel,
            searchMenuTypes: ["filter"],
            searchViewFields: searchViewFields,
        };
    }
}
