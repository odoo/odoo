/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Checkbox } from "@odx_owl/components/checkbox/checkbox";
import { Input } from "@odx_owl/components/input/input";
import { Select } from "@odx_owl/components/select/select";
import { cn } from "@odx_owl/core/utils/cn";
import { resolveDirection } from "@odx_owl/core/utils/direction";

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function formatLabel(value) {
    return String(value || "")
        .replace(/[_-]+/g, " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());
}

function normalizeKey(value) {
    return String(value ?? "");
}

function toComparable(value) {
    if (value === null || value === undefined || value === "") {
        return null;
    }
    const numeric = Number(value);
    if (Number.isFinite(numeric) && String(value).trim() !== "") {
        return numeric;
    }
    return String(value).toLowerCase();
}

export class DataTable extends Component {
    static template = "odx_owl.DataTable";
    static components = {
        Checkbox,
        Input,
        Select,
    };
    static props = {
        className: { type: String, optional: true },
        columns: { type: Array, optional: true },
        data: { type: Array, optional: true },
        dir: { type: String, optional: true },
        emptyDescription: { type: String, optional: true },
        emptyTitle: { type: String, optional: true },
        onPageChange: { type: Function, optional: true },
        onQueryChange: { type: Function, optional: true },
        onRowClick: { type: Function, optional: true },
        onSelectionChange: { type: Function, optional: true },
        onSortChange: { type: Function, optional: true },
        pageSize: { type: Number, optional: true },
        pageSizeOptions: { type: Array, optional: true },
        rowKey: { type: String, optional: true },
        searchableKeys: { type: Array, optional: true },
        searchPlaceholder: { type: String, optional: true },
        selectable: { type: Boolean, optional: true },
        showPagination: { type: Boolean, optional: true },
        showSearch: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        striped: { type: Boolean, optional: true },
        defaultSort: { optional: true, validate: (v) => v === null || v === undefined || (typeof v === "object" && !Array.isArray(v)) },
    };
    static defaultProps = {
        className: "",
        columns: [],
        data: [],
        emptyDescription: "Adjust your search or filters to broaden the result set.",
        emptyTitle: "No matching rows",
        pageSize: 5,
        pageSizeOptions: [5, 10, 20],
        rowKey: "id",
        searchableKeys: [],
        searchPlaceholder: "Search rows...",
        selectable: false,
        showPagination: true,
        showSearch: true,
        striped: false,
    };

    setup() {
        const initialSort = this.props.defaultSort || {};
        this.state = useState({
            page: 1,
            pageSize: this.props.pageSize,
            query: "",
            selectedKeys: [],
            sortDirection: initialSort.direction || "asc",
            sortKey: initialSort.key || null,
        });
    }

    get classes() {
        return cn(
            "odx-data-table",
            {
                "odx-data-table--striped": this.props.striped,
            },
            this.props.className
        );
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get columnCount() {
        return this.normalizedColumns.length + (this.props.selectable ? 1 : 0) + (this.hasRowActions ? 1 : 0);
    }

    get dataRows() {
        return Array.isArray(this.props.data) ? this.props.data : [];
    }

    get hasRowActions() {
        return Boolean(this.props.slots?.row_actions);
    }

    get hasToolbarActions() {
        return Boolean(this.props.slots?.toolbar_actions);
    }

    get normalizedColumns() {
        return (this.props.columns || []).map((column, index) => ({
            align: column.align || "start",
            className: column.className || "",
            descriptionAccessor: column.descriptionAccessor,
            descriptionKey: column.descriptionKey,
            formatter: column.formatter,
            key: column.key || `column-${index}`,
            label: column.label || formatLabel(column.key || `column ${index + 1}`),
            searchable: column.searchable !== false,
            searchAccessor: column.searchAccessor,
            sortable: Boolean(column.sortable),
            sortAccessor: column.sortAccessor,
            type: column.type || "text",
            valueAccessor: column.valueAccessor,
            variant: column.variant,
            variantMap: column.variantMap || {},
        }));
    }

    get pageCount() {
        if (!this.filteredRows.length) {
            return 1;
        }
        return Math.max(1, Math.ceil(this.filteredRows.length / this.state.pageSize));
    }

    get pageSizeOptions() {
        return (this.props.pageSizeOptions || []).map((value) => ({
            label: `${value} rows`,
            value,
        }));
    }

    get query() {
        return this.state.query.trim().toLowerCase();
    }

    get rangeEnd() {
        if (!this.filteredRows.length) {
            return 0;
        }
        return Math.min(this.state.page * this.state.pageSize, this.filteredRows.length);
    }

    get rangeStart() {
        if (!this.filteredRows.length) {
            return 0;
        }
        return (this.state.page - 1) * this.state.pageSize + 1;
    }

    get searchableColumnKeys() {
        if (Array.isArray(this.props.searchableKeys) && this.props.searchableKeys.length) {
            return this.props.searchableKeys;
        }
        return this.normalizedColumns.filter((column) => column.searchable).map((column) => column.key);
    }

    get selectedCount() {
        return this.state.selectedKeys.length;
    }

    get toolbarSlotProps() {
        return {
            filteredCount: this.filteredRows.length,
            query: this.state.query,
            selectedCount: this.selectedCount,
            totalCount: this.dataRows.length,
        };
    }

    get visibleRows() {
        const start = (this.state.page - 1) * this.state.pageSize;
        return this.sortedRows.slice(start, start + this.state.pageSize);
    }

    get visibleRowKeys() {
        return this.visibleRows.map((row, index) => normalizeKey(this.getRowId(row, index)));
    }

    get allVisibleSelected() {
        return Boolean(this.visibleRows.length) && this.visibleRowKeys.every((key) => this.state.selectedKeys.includes(key));
    }

    get filteredRows() {
        if (!this.query) {
            return this.dataRows;
        }
        return this.dataRows.filter((row) => {
            return this.searchableColumnKeys.some((key) => {
                const column = this.normalizedColumns.find((item) => item.key === key) || { key };
                const value = this.getSearchValue(column, row);
                return String(value || "").toLowerCase().includes(this.query);
            });
        });
    }

    get sortedRows() {
        const rows = [...this.filteredRows];
        if (!this.state.sortKey) {
            return rows;
        }
        const column = this.normalizedColumns.find((item) => item.key === this.state.sortKey);
        if (!column) {
            return rows;
        }
        const direction = this.state.sortDirection === "desc" ? -1 : 1;
        rows.sort((left, right) => {
            const leftValue = toComparable(this.getSortValue(column, left));
            const rightValue = toComparable(this.getSortValue(column, right));
            if (leftValue === rightValue) {
                return 0;
            }
            if (leftValue === null) {
                return 1;
            }
            if (rightValue === null) {
                return -1;
            }
            if (typeof leftValue === "number" && typeof rightValue === "number") {
                return (leftValue - rightValue) * direction;
            }
            return String(leftValue).localeCompare(String(rightValue)) * direction;
        });
        return rows;
    }

    getCellClasses(column, row) {
        return cn(
            "odx-data-table__cell",
            `odx-data-table__cell--align-${column.align}`,
            {
                "odx-data-table__cell--badge": column.type === "badge",
                "odx-data-table__cell--numeric": column.type === "number",
            },
            column.className,
            this.props.onRowClick ? "odx-data-table__cell--interactive" : ""
        );
    }

    getCellDescription(column, row) {
        if (typeof column.descriptionAccessor === "function") {
            return column.descriptionAccessor(row, this.getCellValue(column, row), column);
        }
        if (column.descriptionKey) {
            return row[column.descriptionKey];
        }
        return "";
    }

    getCellText(column, row) {
        const value = this.getCellValue(column, row);
        if (typeof column.formatter === "function") {
            return column.formatter(value, row, column);
        }
        if (column.type === "number") {
            const number = Number(value);
            return Number.isFinite(number) ? number.toLocaleString() : "";
        }
        return value ?? "";
    }

    getCellValue(column, row) {
        if (typeof column.valueAccessor === "function") {
            return column.valueAccessor(row, column);
        }
        return row[column.key];
    }

    getHeaderClasses(column) {
        return cn(
            "odx-data-table__head",
            `odx-data-table__head--align-${column.align}`,
            {
                "odx-data-table__head--sortable": column.sortable,
            }
        );
    }

    getSortButtonClasses(column) {
        return cn("odx-data-table__sort", {
            "odx-data-table__sort--active": this.state.sortKey === column.key,
        });
    }

    getRowClasses(row, index) {
        return cn("odx-data-table__row", {
            "odx-data-table__row--selected": this.isSelected(row, index),
            "odx-data-table__row--clickable": Boolean(this.props.onRowClick),
        });
    }

    getRowDomKey(row, index) {
        return `${this.getRowId(row, index)}-${index}`;
    }

    getRowId(row, index) {
        return row?.[this.props.rowKey] ?? index;
    }

    getRowSlotProps(row, index) {
        return {
            index,
            row,
            rowId: this.getRowId(row, index),
            selected: this.isSelected(row, index),
        };
    }

    getSearchValue(column, row) {
        if (typeof column.searchAccessor === "function") {
            return column.searchAccessor(row, column);
        }
        return this.getCellValue(column, row);
    }

    getSortLabel(column) {
        if (this.state.sortKey !== column.key) {
            return `${column.label}, sortable`;
        }
        return `${column.label}, sorted ${this.state.sortDirection === "desc" ? "descending" : "ascending"}`;
    }

    getSortState(column) {
        if (this.state.sortKey !== column.key) {
            return "none";
        }
        return this.state.sortDirection === "desc" ? "descending" : "ascending";
    }

    getSortValue(column, row) {
        if (typeof column.sortAccessor === "function") {
            return column.sortAccessor(row, column);
        }
        return this.getCellValue(column, row);
    }

    getStatusClasses(column, row) {
        const value = this.getCellValue(column, row);
        const variant = typeof column.variant === "function"
            ? column.variant(value, row, column)
            : column.variantMap?.[value] || column.variant || "default";
        return cn(
            "odx-data-table__status",
            `odx-data-table__status--${variant}`
        );
    }

    handlePageSizeChange(value) {
        const nextSize = clamp(Number(value) || this.props.pageSize, 1, 500);
        this.state.pageSize = nextSize;
        this.state.page = 1;
        this.props.onPageChange?.(1, nextSize);
    }

    handleRowClick(row, index, ev) {
        if (!this.props.onRowClick) {
            return;
        }
        if (ev.target.closest("button, a, input, select, textarea, [role='checkbox']")) {
            return;
        }
        this.props.onRowClick?.(row, index, ev);
    }

    isSelected(row, index) {
        return this.state.selectedKeys.includes(normalizeKey(this.getRowId(row, index)));
    }

    setPage(page) {
        const nextPage = clamp(page, 1, this.pageCount);
        this.state.page = nextPage;
        this.props.onPageChange?.(nextPage, this.state.pageSize);
    }

    setQuery(value) {
        this.state.query = value;
        this.state.page = 1;
        this.props.onQueryChange?.(value);
    }

    toggleColumnSort(column) {
        if (!column.sortable) {
            return;
        }
        if (this.state.sortKey !== column.key) {
            this.state.sortKey = column.key;
            this.state.sortDirection = "asc";
        } else if (this.state.sortDirection === "asc") {
            this.state.sortDirection = "desc";
        } else {
            this.state.sortKey = null;
            this.state.sortDirection = "asc";
        }
        this.state.page = 1;
        this.props.onSortChange?.(
            this.state.sortKey
                ? { key: this.state.sortKey, direction: this.state.sortDirection }
                : null
        );
    }

    toggleRowSelection(row, index, checked) {
        const key = normalizeKey(this.getRowId(row, index));
        const selected = new Set(this.state.selectedKeys);
        if (checked) {
            selected.add(key);
        } else {
            selected.delete(key);
        }
        this.state.selectedKeys = [...selected];
        this.props.onSelectionChange?.(this.state.selectedKeys);
    }

    toggleVisibleSelection(checked) {
        const selected = new Set(this.state.selectedKeys);
        for (const key of this.visibleRowKeys) {
            if (checked) {
                selected.add(key);
            } else {
                selected.delete(key);
            }
        }
        this.state.selectedKeys = [...selected];
        this.props.onSelectionChange?.(this.state.selectedKeys);
    }
}
