import { Component, useRef, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService, useAutofocus } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { basicContainerBuilderComponentProps } from "./utils";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Dropdown } from "@web/core/dropdown/dropdown";

export class BasicMany2ManySearchInput extends Component {
    static template = "html_builder.BasicMany2ManySearchInput";
    static props = {
        onSearch: Function,
    };
    setup() {
        useAutofocus();
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
        // createAction: { type: String, optional: true },
        selection: { type: Array, element: Object },
        setSelection: Function,
        canCreate: { type: Boolean, optional: true },
    };
    static defaultProps = {
        fields: [],
        domain: [],
        limit: 10,
        canCreate: false,
    };
    static components = { Dropdown, DropdownItem, BasicMany2ManySearchInput };

    setup() {
        this.orm = useService("orm");
        this.createInputRef = useRef("createInput");
        this.state = useState({
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
    search(ev) {
        this._search(ev.target.value);
    }
    async _search(searchValue) {
        const tuples = await this.orm.call(this.props.model, "name_search", [], {
            name: searchValue,
            args: Object.values(this.props.domain).filter((item) => item !== null),
            operator: "ilike",
            limit: this.props.limit + 1,
        });
        this.state.searchResults = [];
        for (const tuple of tuples) {
            this.state.searchResults.push({
                id: tuple[0],
                name: tuple[1],
            });
        }
        /* TODO handle types
        const records = await this.orm.read(
            this.props.model,
            tuples.map(([id, _name]) => id),
            this.props.fields
        );
        */
    }
    select(entry) {
        this.props.setSelection([...this.props.selection, entry]);
    }
    unselect(id) {
        this.props.setSelection([...this.props.selection.filter((item) => item.id !== id)]);
    }
    create() {
        // const name = this.createInputRef.el.value;
        // TODO implement create ?
    }
}
