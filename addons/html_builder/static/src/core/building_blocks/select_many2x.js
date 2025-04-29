import { Component, useState, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useCachedModel } from "@html_builder/core/cached_model_utils";
import { _t } from "@web/core/l10n/translation";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useDropdownCloser } from "@web/core/dropdown/dropdown_hooks";

class SelectMany2XCreate extends Component {
    static template = "html_builder.SelectMany2XCreate";
    static props = {
        name: String,
        create: Function,
    };

    setup() {
        this.dropdown = useDropdownCloser();
        this.create = this.create.bind(this);
    }

    create() {
        this.dropdown.close();
        this.props.create(this.props.name);
    }
}

export class SelectMany2X extends Component {
    static template = "html_builder.SelectMany2X";
    static props = {
        model: String,
        fields: { type: Array, element: String, optional: true },
        domain: { type: Array, optional: true },
        limit: { type: Number, optional: true },
        selected: {
            type: Array,
            element: { type: Object, shape: { id: [Number, String], "*": true } },
        },
        select: Function,
        closeOnEnterKey: { type: Boolean, optional: true },
        message: { type: String, optional: true },
        create: { type: Function, optional: true },
    };
    static defaultProps = {
        fields: [],
        domain: [],
        limit: 5,
        closeOnEnterKey: true,
        message: _t("Choose a record..."),
    };
    static components = { SelectMenu, SelectMany2XCreate };

    setup() {
        this.orm = useService("orm");
        this.cachedModel = useCachedModel();
        this.state = useState({
            nameToCreate: "",
            searchResults: [],
            limit: this.props.limit,
        });
        onWillUpdateProps(async (newProps) => {
            if (this.searchInvalidationKey(this.props) !== this.searchInvalidationKey(newProps)) {
                this.state.searchResults = [];
            }
        });
    }
    searchInvalidationKey(props) {
        return JSON.stringify([props.model, props.fields, props.domain]);
    }
    searchMore(searchValue) {
        this.state.limit += this.props.limit;
        this.search(searchValue);
    }
    async search(searchValue) {
        const tuples = await this.orm.call(this.props.model, "name_search", [], {
            name: searchValue,
            domain: Object.values(this.props.domain).filter((item) => item !== null),
            operator: "ilike",
            limit: this.state.limit + 1,
        });
        this.state.hasMore = tuples.length > this.state.limit;
        this.state.searchResults = await this.cachedModel.ormRead(
            this.props.model,
            tuples.slice(0, this.state.limit).map(([id, _name]) => id),
            [...new Set(this.props.fields).add("display_name").add("name")]
        );
    }
    filteredSearchResult() {
        const selectedIds = new Set(this.props.selected.map((e) => e.id));
        return this.state.searchResults.filter((entry) => !selectedIds.has(entry.id));
    }
    async canCreate(name) {
        if (!this.props.create || !name.length) {
            return false;
        }
        const allRecords = await this.cachedModel.ormSearchRead(
            this.props.model,
            [],
            ["id", "name"]
        );
        const usedNames = [
            // Exclude existing names
            ...allRecords.map((item) => item.name),
            // Exclude new names
            ...this.props.selected.map((item) => item.name),
        ];
        return !usedNames.includes(name);
    }
    async onInput(searchValue) {
        this.search(searchValue);
        this.state.nameToCreate = (await this.canCreate(searchValue)) ? searchValue : "";
    }
}
