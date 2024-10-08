import { Component, onMounted, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";
import { SearchBar } from "../search_bar/search_bar";

export class CustomListView extends Component {
    static template = "point_of_sale.CustomListView";
    static components = { SearchBar };
    static props = {
        model: String,
        slots: { type: Object, optional: true },
        onClickLine: { type: Function, optional: true },
        selectedRecord: { type: Object | undefined, optional: true },
        onFiltered: { type: Function, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.viewService = useService("view");
        this.ui = useService("ui");
        this.state = useState({
            records: [],
            sortField: this.fields.list[0],
            sortOrder: "asc",
            filter: {
                searchField: "",
                searchValue: "",
                filterField: "",
                filterValue: "",
            },
        });

        onMounted(() => {
            this.recomputeRecords();
        });
    }

    get model() {
        return this.props.model;
    }

    get firstRecord() {
        return this.pos.models[this.model].getFirst();
    }

    get fields() {
        return this.firstRecord.customListFields;
    }

    get defaults() {
        return this.firstRecord.customListDefaults;
    }

    get filters() {
        return this.firstRecord.customListFilters;
    }

    get searches() {
        return this.firstRecord.customListSearches;
    }

    get modelFields() {
        return this.pos.models[this.model].modelFields;
    }

    getSelectionValues(field) {
        return this.pos.data.viewSearch[this.model].models[this.model].fields[field].selection;
    }

    getFieldName(field) {
        return this.modelFields[field].string;
    }

    getFieldValue(field, record) {
        return this.searches[field](record) || "";
    }

    setFieldSort(field) {
        this.state.sortField = field;
        this.state.sortOrder = this.state.sortOrder === "asc" ? "desc" : "asc";
        this.changeRecordSort();
    }

    changeRecordSort() {
        this.state.records.sort((a, b) => {
            const fieldA = a[this.state.sortField];
            const fieldB = b[this.state.sortField];
            if (fieldA < fieldB) {
                return this.state.sortOrder === "asc" ? -1 : 1;
            }
            if (fieldA > fieldB) {
                return this.state.sortOrder === "asc" ? 1 : -1;
            }
            return 0;
        });
    }

    async onFilterChange(payload) {
        this.recomputeRecords(payload);
    }

    recomputeRecords(payload = false) {
        let records = this.pos.models[this.model].getAll();
        const filter = payload || this.state.filter;
        const filterF = filter.filterField;
        const filterV = filter.filterValue;
        const searchF = filter.searchField;
        const searchV = filter.searchValue;

        this.state.filter = {
            searchField: searchF,
            searchValue: searchV,
            filterField: filterF,
            filterValue: filterV,
        };

        let addSelected = false;
        records = records.filter((r) => {
            if (filterF && filterV && r.customListFilters[filterF].fn(r) !== filterV) {
                return false;
            }
            if (r === this.props.selectedRecord) {
                addSelected = true;
                return false;
            }
            return true;
        });

        if (searchF && searchV) {
            records = fuzzyLookup(searchV, records, this.searches[searchF]);
        } else if (searchV && this.firstRecord.searchString) {
            records = fuzzyLookup(searchV, records, (r) => r.searchString);
        }

        if (this.props.selectedRecord && addSelected) {
            records.unshift(this.props.selectedRecord);
        }

        this.state.records = records;
        this.props.onFiltered && this.props.onFiltered(records);
    }

    async loadMoreRecords() {
        const domain = [
            [
                "id",
                "not in",
                this.state.records.filter((r) => typeof r.id === "number").map((r) => r.id),
            ],
        ];

        if (this.state.filter.filterValue) {
            domain.push([this.state.filter.filterField, "=", this.state.filter.filterValue]);
        }

        if (this.state.filter.searchValue) {
            domain.push([this.state.filter.searchField, "ilike", this.state.filter.searchValue]);
        }

        try {
            await this.pos.data.searchRead(this.model, domain, [], {
                limit: 30,
            });
        } catch {
            console.info("LIST: Unable to load more records");
        }

        this.recomputeRecords();
    }
}
