import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { fuzzyLookup } from "@web/core/utils/search";

export class BuilderListDialog extends Component {
    static template = "html_builder.BuilderListDialog";
    static components = { Dialog };
    static props = {
        excludedRecords: { type: Array },
        includedRecords: { type: Array },
        close: { type: Function },
        save: { type: Function },
    };

    setup() {
        this.state = useState({
            excludedRecords: [...this.props.excludedRecords].sort(this.sortByName),
            includedRecords: [...this.props.includedRecords],
            searchString: "",
        });
    }

    save() {
        this.props.save(this.state.includedRecords);
        this.props.close();
    }

    get searchExcluded() {
        if (!this.state.searchString) {
            return this.state.excludedRecords;
        }
        return fuzzyLookup(
            this.state.searchString,
            this.state.excludedRecords,
            (record) => record.display_name
        );
    }

    get searchIncluded() {
        if (!this.state.searchString) {
            return this.state.includedRecords;
        }
        return fuzzyLookup(
            this.state.searchString,
            this.state.includedRecords,
            (record) => record.display_name
        );
    }

    onSearch(ev) {
        this.state.searchString = ev.target.value;
    }

    include(record) {
        const index = this.state.excludedRecords.indexOf(record);
        this.state.includedRecords.push(...this.state.excludedRecords.splice(index, 1));
    }

    exclude(record) {
        const index = this.state.includedRecords.indexOf(record);
        this.state.excludedRecords.push(...this.state.includedRecords.splice(index, 1));
        this.sortExcluded();
    }

    includeAll() {
        this.state.includedRecords.push(...this.state.excludedRecords.splice(0));
    }

    excludeAll() {
        this.state.excludedRecords.push(...this.state.includedRecords.splice(0));
        this.sortExcluded();
    }

    sortExcluded() {
        this.state.excludedRecords.sort((a, b) =>
            (a.display_name || "").localeCompare(b.display_name || "")
        );
    }
}
