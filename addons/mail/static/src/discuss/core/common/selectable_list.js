import { Component, useState } from "@odoo/owl";

/**
 * Base component for a searchable list with multi-selection.
 */
export class SelectableList extends Component {
    static template = "mail.SelectableList";
    static props = {
        close: Function,
        maxSelections: { type: Number, optional: true },
        title: String,
        searchPlaceholder: { type: String, optional: true },
    };
    static defaultProps = {
        maxSelections: 5,
        searchPlaceholder: "",
    };

    setup() {
        super.setup();
        this.state = useState({
            searchStr: "",
            selectedKeys: [],
        });
    }

    get maxSelections() {
        return this.props.maxSelections;
    }

    get searchStr() {
        return this.state.searchStr;
    }

    set searchStr(value) {
        this.state.searchStr = value;
    }

    get selectedKeys() {
        return this.state.selectedKeys;
    }

    /**
     * @returns {Array<{ key: string, label: string, record: any }>}
     */
    get selectableOptions() {
        return [];
    }

    isSelected(key) {
        return this.selectedKeys.includes(key);
    }

    toggleSelection(key) {
        if (this.isSelected(key)) {
            this.state.selectedKeys = this.selectedKeys.filter((k) => k !== key);
        } else if (this.selectedKeys.length < this.maxSelections) {
            this.state.selectedKeys = [...this.selectedKeys, key];
        }
    }

    get canSend() {
        return this.selectedKeys.length > 0;
    }
}
