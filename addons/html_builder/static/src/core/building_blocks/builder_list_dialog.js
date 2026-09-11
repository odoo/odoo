import { Component, computed, proxy, useProps, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { fuzzyLookup } from "@web/core/utils/search";
import { localeCompare } from "@web/core/l10n/utils";

export class BuilderListDialog extends Component {
    static template = "html_builder.BuilderListDialog";
    static components = { Dialog };
    props = useProps({
        excludedRecords: t.array(),
        includedRecords: t.array(),
        close: t.function(),
        save: t.function(),
    });

    setup() {
        this.state = proxy({
            excludedRecords: [...this.props.excludedRecords].sort(this.sortByName),
            includedRecords: [...this.props.includedRecords],
            searchString: "",
        });
        this.searchExcluded = computed(() => this.search(this.state.excludedRecords));
        this.searchIncluded = computed(() => this.search(this.state.includedRecords));
    }

    save() {
        this.props.save(this.state.includedRecords);
        this.props.close();
    }

    search(records) {
        if (!this.state.searchString) {
            return records;
        }
        return fuzzyLookup(this.state.searchString, records, (record) => record.display_name);
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
        this.state.excludedRecords.sort((a, b) => localeCompare(a.display_name, b.display_name));
    }
}
