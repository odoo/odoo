import { Component, useRef, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService, useAutofocus } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { basicContainerBuilderComponentProps } from "./utils";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useCachedModel } from "@html_builder/core/plugins/cached_model_utils";

export class BasicMany2ManySearchInput extends Component {
    static template = "html_builder.BasicMany2ManySearchInput";
    static props = {
        onSearch: Function,
        toFocus: Function,
    };
    setup() {
        useAutofocus();
        const inputRef = useRef("autofocus");
        this.props.toFocus(() => inputRef.el.focus());
    }
}

export class BasicMany2Many extends Component {
    static template = "html_builder.BasicMany2Many";
    static props = {
        ...basicContainerBuilderComponentProps,
        model: String,
        fields: { type: Array, element: String, optional: true },
        domain: { type: Array, optional: true },
        limit: { type: Number, optional: true },
        selection: { type: Array, element: Object },
        setSelection: Function,
        create: { type: Function, optional: true },
    };
    static defaultProps = {
        fields: [],
        domain: [],
        limit: 10,
    };
    static components = { Dropdown, DropdownItem, BasicMany2ManySearchInput };

    setup() {
        this.searchInputFocusCallback = undefined;
        this.orm = useService("orm");
        this.cachedModel = useCachedModel();
        this.openerRef = useRef("opener");
        this.createInputRef = useRef("createInput");
        this.state = useState({
            createEnabled: false,
            searchResults: [],
        });
        this.onSearch = debounce(this.search.bind(this), 300);
        onWillStart(async () => {
            await this.handleProps(this.props);
        });
        onWillUpdateProps(async (newProps) => {
            await this.handleProps(newProps);
        });
    }
    async handleProps(props) {
        this.state.searchResults = [];
    }
    setSearchInputFocusCallback(callback) {
        this.searchInputFocusCallback = callback;
    }
    search(ev) {
        this._search(ev.target.value);
    }
    searchMore() {
        this.searchInputFocusCallback();
    }
    async _search(searchValue) {
        const tuples = await this.orm.call(this.props.model, "name_search", [], {
            name: searchValue,
            args: Object.values(this.props.domain).filter((item) => item !== null),
            operator: "ilike",
            limit: this.props.limit + 1,
        });
        this.state.searchMore = tuples.length > this.props.limit;
        if (this.props.fields.length) {
            const fields = this.props.fields.includes("name")
                ? this.props.fields
                : ["name", ...this.props.fields];
            this.state.searchResults = await this.cachedModel.ormRead(
                this.props.model,
                tuples.map(([id, _name]) => id),
                fields
            );
        } else {
            this.state.searchResults = [];
            for (const tuple of tuples.slice(0, this.props.limit)) {
                this.state.searchResults.push({
                    id: tuple[0],
                    name: tuple[1],
                });
            }
        }
    }
    select(entry) {
        this.props.setSelection([...this.props.selection, entry]);
    }
    unselect(id) {
        this.props.setSelection([...this.props.selection.filter((item) => item.id !== id)]);
    }
    async onCreateInput() {
        const name = this.createInputRef.el.value;
        const allRecords = await this.cachedModel.ormSearchRead(
            this.props.model,
            [],
            ["id", "name"]
        );
        const usedNames = [
            // Exclude existing names
            ...allRecords.map((item) => item.name),
            // Exclude new names
            ...this.props.selection.map((item) => item.name),
        ];
        this.state.createEnabled = name.length > 0 && !usedNames.includes(name);
    }
    create() {
        const name = this.createInputRef.el.value;
        this.props.create(name);
        this.openerRef.el.click(); // close dropdown
    }
}
