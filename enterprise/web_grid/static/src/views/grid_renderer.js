/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";
import { useDebounced } from "@web/core/utils/timing";
import { useVirtualGrid } from "@web/core/virtual_grid_hook";
import { Field } from "@web/views/fields/field";
import { Record } from "@web/model/record";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { ViewScaleSelector } from "@web/views/view_components/view_scale_selector";

import { GridComponent } from "@web_grid/components/grid_component/grid_component";

import {
    Component,
    markup,
    useState,
    onWillUpdateProps,
    onMounted,
    onPatched,
    reactive,
    useRef,
    useExternalListener,
} from "@odoo/owl";

export class GridRenderer extends Component {
    static components = {
        Field,
        GridComponent,
        Record,
        ViewScaleSelector,
    };

    static template = "web_grid.Renderer";

    static props = {
        sections: { type: Array, optional: true },
        columns: { type: Array, optional: true },
        rows: { type: Array, optional: true },
        model: { type: Object, optional: true },
        options: Object,
        sectionField: { type: Object, optional: true },
        rowFields: Array,
        measureField: Object,
        isEditable: Boolean,
        widgetPerFieldName: Object,
        openAction: { type: Object, optional: true },
        contentRef: Object,
        createInline: Boolean,
        createRecord: Function,
        ranges: { type: Object, optional: true },
        state: Object,
        toggleWeekendVisibility: Function,
    };

    static defaultProps = {
        sections: [],
        columns: [],
        rows: [],
        model: {},
        ranges: {},
    };

    setup() {
        this.rendererRef = useRef("renderer");
        this.actionService = useService("action");
        this.editionState = useState({
            hoveredCellInfo: false,
            editedCellInfo: false,
        });
        this.hoveredElement = null;
        const measureFieldName = this.props.model.measureFieldName;
        const fieldInfo = this.props.model.fieldsInfo[measureFieldName];
        const measureFieldWidget = this.props.widgetPerFieldName[measureFieldName];
        const widgetName = measureFieldWidget || fieldInfo.type;
        this.gridCell = registry.category("grid_components").get(widgetName);
        this.hoveredCellProps = {
            // props cell hovered
            name: measureFieldName,
            type: widgetName,
            component: this.gridCell.component,
            reactive: reactive({ cell: null }),
            fieldInfo,
            readonly: !this.props.isEditable,
            openRecords: this.openRecords.bind(this),
            editMode: false,
            onEdit: this.onEditCell.bind(this),
            getCell: this.getCell.bind(this),
            isMeasure: true,
        };
        this.editCellProps = {
            // props for cell in edit mode
            name: measureFieldName,
            type: widgetName,
            component: this.gridCell.component,
            reactive: reactive({ cell: null }),
            fieldInfo,
            readonly: !this.props.isEditable,
            openRecords: this.openRecords.bind(this),
            editMode: true,
            onEdit: this.onEditCell.bind(this),
            getCell: this.getCell.bind(this),
            onKeyDown: this.onCellKeydown.bind(this),
            isMeasure: true,
        };
        this.isEditing = false;
        onWillUpdateProps(this.onWillUpdateProps);
        onMounted(this._focusOnToday);
        onPatched(this._focusOnToday);
        // This property is used to avoid refocus on today whenever a cell value is updated.
        this.shouldFocusOnToday = true;
        this.onMouseOver = useDebounced(this._onMouseOver, 10);
        this.onMouseOut = useDebounced(this._onMouseOut, 10);
        this.virtualGrid = useVirtualGrid({
            scrollableRef: this.props.contentRef,
            initialScroll: { top: 60 },
        });
        useExternalListener(window, "click", this.onClick);
        useExternalListener(window, "keydown", this.onKeyDown);
    }

    getCell(rowId, columnId) {
        return this.props.model.data.rows[rowId]?.cells[columnId];
    }

    getItemHeight(item) {
        let height = this.rowHeight;
        if (item.isSection && item.isFake) {
            return 0;
        }
        if (this.props.createInline && !item.isSection && item.section.lastRow.id === item.id) {
            height *= 2; // to include the Add a line row
        }
        return height;
    }

    get isMobile() {
        return this.env.isSmall;
    }

    get rowHeight() {
        const baseHeight = this.isMobile ? 48 : 32;
        /*
         * On mobile devices, grouped by fields are stacked vertically.
         * By default, the base height accommodates up to 2 fields.
         * For each additional field beyond the first 2, we add 20px to maintain proper spacing.
         */
        const extraHeight = this.isMobile
            ? Math.max(0, this.props.model.rowFields.length - 2) * 20
            : 0;
        return baseHeight + extraHeight;
    }

    get virtualRows() {
        this.virtualGrid.setRowsHeights(this.props.rows.map((row) => this.getItemHeight(row)));
        const [start, end] = this.virtualGrid.rowsIndexes;
        return this.props.rows.slice(start, end + 1);
    }

    getRowPosition(row, isCreateInlineRow = false) {
        const rowIndex = row ? this.props.rows.findIndex((r) => r.id === row.id) : 0;
        const section = row && row.getSection();
        const sectionDisplayed = Boolean(section && (section.value || this.props.sections.length > 1));
        let rowPosition = this.rowsGap + rowIndex + 1 + (sectionDisplayed ? section.sectionId : 0);
        if (isCreateInlineRow) {
            rowPosition += 1;
        }
        if (!sectionDisplayed) {
            rowPosition -= 1;
        }
        return rowPosition;
    }

    getTotalRowPosition() {
        let sectionIndex = 0;
        if (this.props.model.sectionField && this.props.sections.length) {
            if (this.props.sections.length > 1 || this.props.sections[0].value) {
                sectionIndex = this.props.sections.length;
            }
        }
        return (
            (this.props.rows.length || 1) +
            sectionIndex +
            (this.props.createInline ? 1 : 0) +
            this.rowsGap
        );
    }

    onWillUpdateProps(nextProps) {}

    formatValue(value) {
        return this.gridCell.formatter(value);
    }

    /**
     * @deprecated
     * TODO: [XBO] remove me in master
     * @param {*} data
     */
    getDefaultState(data) {
        return {};
    }

    get rowsCount() {
        const addLineRows = this.props.createInline ? this.props.sections.length || 1 : 0;
        return this.props.rows.length - (this.props.model.sectionField ? 0 : 1) + addLineRows;
    }

    get gridTemplateRows() {
        let totalRows = 0;
        if (!this.props.options.hideColumnTotal) {
            totalRows += 1;
            if (this.props.options.hasBarChartTotal) {
                totalRows += 1;
            }
        }
        // Row height must be hard-coded for the virtual hook to work properly.
        return `auto repeat(${this.rowsCount + totalRows}, ${this.rowHeight}px)`;
    }

    get gridTemplateColumns() {
        return `auto repeat(${this.props.columns.length}, ${
            this.props.columns.length > 7 ? "minmax(8ch, auto)" : "minmax(10ch, 1fr)"
        }) minmax(10ch, 10em)`;
    }

    get measureLabel() {
        const measureFieldName = this.props.model.measureFieldName;
        if (measureFieldName === "__count") {
            return _t("Total");
        }
        return (
            this.props.measureField.string || this.props.model.fieldsInfo[measureFieldName].string
        );
    }

    get rowsGap() {
        return 1;
    }

    get columnsGap() {
        return 1;
    }

    get displayAddLine() {
        return this.props.createInline && this.row.id === this.row.section.lastRow.id;
    }

    getCellColorClass(column) {
        return "text-900";
    }

    getSectionColumnsClasses(column, row) {
        const isToday = column.isToday;
        return {
            'bg-info bg-opacity-50': isToday,
            'bg-200 border-top': !isToday,
            'bg-opacity-75': this.getUnavailableClass(column) === 'o_grid_unavailable' && row.cells[column.id].value === 0,
        }
    }

    getSectionCellsClasses(column, row) {
        return {
            'text-opacity-25' : row.cells[column.id].value === 0 || this.getUnavailableClass(column) === 'o_grid_unavailable',
        };
    }

    isTextDanger() {
        return false;
    }

    getTextColorClasses(column, row, isEven) {
        const value = row.cells[column.id].value;
        const isTextDanger = this.isTextDanger(row, column);
        return {
            'text-bg-view': isEven && value >= 0 && !isTextDanger,
            'text-900': !isEven && value >= 0 && !isTextDanger,
            'text-danger': value < 0 || isTextDanger,
        }
    }

    getCellsClasses(column, row, section, isEven) {
        return {
            ...this.getTextColorClasses(column, row, isEven),
            'o_grid_cell_today': column.isToday,
            'fst-italic': row.isAdditionalRow,
        };
    }

    _getSectionTotalCellBgColor(section) {
        return 'text-bg-800';
    }

    getSectionTotalRowClass(section, grandTotal) {
        return {
            [this._getSectionTotalCellBgColor(section)]: true,
            'text-opacity-25': grandTotal === 0,
        };
    }

    getColumnBarChartHeightStyle(column) {
        let heightPercentage = 0;
        if (this.props.model.maxColumnsTotal !== 0) {
            heightPercentage = (column.grandTotal / this.props.model.maxColumnsTotal) * 100;
        }
        return `height: ${heightPercentage}%; bottom: 0;`;
    }

    getFooterTotalCellClasses(grandTotal) {
        if (grandTotal < 0) {
            return "bg-danger text-bg-danger";
        }

        return "bg-400";
    }

    getUnavailableClass(column, section = undefined) {
        return "";
    }

    getFieldAdditionalProps(fieldName) {
        return {
            name: fieldName,
            type: this.props.widgetPerFieldName[fieldName] || this.props.model.fieldsInfo[fieldName].type,
        };
    }

    onCreateInlineClick(section) {
        const context = {
            ...(section?.context || {}),
        };
        const title = _t("Add a Line");
        this.props.createRecord({ context, title });
    }

    _focusOnToday() {
        if (!this.shouldFocusOnToday) {
            return;
        }
        this.shouldFocusOnToday = false;
        const { navigationInfo, columnFieldIsDate } = this.props.model;
        if (this.isMobile || !columnFieldIsDate || navigationInfo.range.name != "month"){
            return;
        }
        const rendererEl = this.rendererRef.el;
        const todayEl = rendererEl.querySelector("div.o_grid_column_title.fw-bolder");
        if (todayEl) {
            rendererEl.parentElement.scrollLeft = todayEl.offsetLeft - rendererEl.offsetWidth / 2 + todayEl.offsetWidth / 2;
        }
    }

    _onMouseOver(ev) {
        if (this.hoveredElement || ev.fromElement?.classList.contains("dropdown-item")) {
            // As mouseout is call prior to mouseover, if hoveredElement is set this means
            // that we haven't left it. So it's a mouseover inside it.
            return;
        }
        const highlightableElement = ev.target.closest(".o_grid_highlightable");
        if (!highlightableElement) {
            // We are not in an element that should trigger a highlight.
            return;
        }
        const { column, gridRow, gridColumn, row } = highlightableElement.dataset;
        const isCellInColumnTotalHighlighted =
            highlightableElement.classList.contains("o_grid_row_total");
        const elementsToHighlight = this.rendererRef.el.querySelectorAll(
            `.o_grid_highlightable[data-grid-row="${gridRow}"]:not(.o_grid_add_line):not(.o_grid_column_title), .o_grid_highlightable[data-grid-column="${gridColumn}"]:not(.o_grid_row_timer):not(.o_grid_section_title):not(.o_grid_row_title${
                isCellInColumnTotalHighlighted ? ",.o_grid_row_total" : ""
            })`
        );
        for (const node of elementsToHighlight) {
            if (node.classList.contains("o_grid_bar_chart_container")) {
                node.classList.add("o_grid_highlighted");
            }
            if (node.dataset.gridRow === gridRow) {
                node.classList.add("o_grid_highlighted");
                if (node.dataset.gridColumn === gridColumn) {
                    node.classList.add("o_grid_cell_highlighted");
                } else {
                    node.classList.add("o_grid_row_highlighted");
                }
            }
        }
        this.hoveredElement = highlightableElement;
        const cell = this.editCellProps.reactive.cell;
        if (
            row &&
            column &&
            !(cell && cell.dataset.row === row && cell.dataset.column === column)
        ) {
            this.hoveredCellProps.reactive.cell = highlightableElement;
        }
    }

    /**
     * Mouse out handler
     *
     * @param {MouseEvent} ev
     */
    _onMouseOut(ev) {
        if (!this.hoveredElement) {
            // If hoveredElement is not set this means were not in a o_grid_highlightable. So ignore it.
            return;
        }
        /** @type {HTMLElement | null} */
        let relatedTarget = ev.relatedTarget;
        const gridCell = relatedTarget?.closest(".o_grid_cell");
        if (
            gridCell &&
            gridCell.dataset.gridRow === this.hoveredElement.dataset.gridRow &&
            gridCell.dataset.gridColumn === this.hoveredElement.dataset.gridColumn &&
            gridCell !== this.editCellProps.reactive.cell
        ) {
            return;
        }
        while (relatedTarget) {
            // Go up the parent chain
            if (relatedTarget === this.hoveredElement) {
                // Check that we are still inside hoveredConnector.
                // If so it means it is a transition between child elements so ignore it.
                return;
            }
            relatedTarget = relatedTarget.parentElement;
        }
        const { gridRow, gridColumn } = this.hoveredElement.dataset;
        const elementsHighlighted = this.rendererRef.el.querySelectorAll(
            `.o_grid_highlightable[data-grid-row="${gridRow}"], .o_grid_highlightable[data-grid-column="${gridColumn}"]`
        );
        for (const node of elementsHighlighted) {
            node.classList.remove(
                "o_grid_highlighted",
                "o_grid_row_highlighted",
                "o_grid_cell_highlighted"
            );
        }
        this.hoveredElement = null;
        if (this.hoveredCellProps.reactive.cell) {
            this.hoveredCellProps.reactive.cell
                .querySelector(".o_grid_cell_readonly")
                .classList.remove("d-none");
            this.hoveredCellProps.reactive.cell = null;
        }
    }

    onEditCell(value) {
        if (this.editCellProps.reactive.cell) {
            this.editCellProps.reactive.cell
                .querySelector(".o_grid_cell_readonly")
                .classList.remove("d-none");
        }
        if (value) {
            this.editCellProps.reactive.cell = this.hoveredCellProps.reactive.cell;
            this.hoveredCellProps.reactive.cell = null;
        } else {
            this.editCellProps.reactive.cell = null;
        }
    }

    _onKeyDown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "escape" && this.editCellProps.reactive.cell) {
            this.onEditCell(false);
        }
    }

    /**
     * Handle click on any element in the grid
     *
     * @param {MouseEvent} ev
     */
    onClick(ev) {
        if (
            !this.editCellProps.reactive.cell ||
            ev.target.closest(".o_grid_highlighted") ||
            ev.target.closest(".o_grid_cell")
        ) {
            return;
        }
        this.onEditCell(false);
    }

    onKeyDown(ev) {
        this._onKeyDown(ev);
    }

    /**
     * Handle the click on a cell in mobile
     *
     * @param {MouseEvent} ev
     */
    onCellClick(ev) {
        ev.stopPropagation();
        const cell = ev.target.closest(".o_grid_highlightable");
        const { row, column } = cell.dataset;
        if (row && column) {
            if (this.editCellProps.reactive.cell) {
                this.editCellProps.reactive.cell
                    .querySelector(".o_grid_cell_readonly")
                    .classList.remove("d-none");
            }
            this.editCellProps.reactive.cell = cell;
        }
    }

    /**
     * Handle keydown when cell is edited in the grid view.
     *
     * @param {KeyboardEvent} ev
     * @param {import("./grid_model").GridCell | null} cell
     */
    onCellKeydown(ev, cell) {
        const hotkey = getActiveHotkey(ev);
        if (!this.rendererRef.el || !cell || !["tab", "shift+tab", "enter"].includes(hotkey)) {
            this._onKeyDown(ev);
            return;
        }
        // Purpose: prevent browser defaults
        ev.preventDefault();
        // Purpose: stop other window keydown listeners (e.g. home menu)
        ev.stopImmediatePropagation();
        let rowId = cell.row.id;
        let columnId = cell.column.id;
        const columnIds = this.props.columns.map((c) => c.id);
        const rowIds = [];
        for (const item of this.props.rows) {
            if (!item.isSection) {
                rowIds.push(item.id);
            }
        }
        let columnIndex = columnIds.indexOf(columnId);
        let rowIndex = rowIds.indexOf(rowId);
        if (hotkey === "tab") {
            columnIndex += 1;
            rowIndex += 1;
            if (columnIndex < columnIds.length) {
                columnId = columnIds[columnIndex];
            } else {
                columnId = columnIds[0];
                if (rowIndex < rowIds.length) {
                    rowId = rowIds[rowIndex];
                } else {
                    rowId = rowIds[0];
                }
            }
        } else if (hotkey === "shift+tab") {
            columnIndex -= 1;
            rowIndex -= 1;
            if (columnIndex >= 0) {
                columnId = columnIds[columnIndex];
            } else {
                columnId = columnIds[columnIds.length - 1];
                if (rowIndex >= 0) {
                    rowId = rowIds[rowIndex];
                } else {
                    rowId = rowIds[rowIds.length - 1];
                }
            }
        } else if (hotkey === "enter") {
            rowIndex += 1;
            if (rowIndex >= rowIds.length) {
                columnIndex = (columnIndex + 1) % columnIds.length;
                columnId = columnIds[columnIndex];
            }
            rowIndex = rowIndex % rowIds.length;
            rowId = rowIds[rowIndex];
        }
        this.onEditCell(false);
        this.hoveredCellProps.reactive.cell = this.rendererRef.el.querySelector(
            `.o_grid_highlightable[data-row="${rowId}"][data-column="${columnId}"]`
        );
        this.onEditCell(true);
    }

    async openRecords(actionTitle, domain, context) {
        const resModel = this.props.model.resModel;
        if (this.props.openAction) {
            const resIds = await this.props.model.orm.search(resModel, domain);
            this.actionService.doActionButton({
                ...this.props.openAction,
                resModel,
                resIds,
                context,
            });
        } else {
            // retrieve form and list view ids from the action
            const { views = [] } = this.env.config;
            const openRecordsViews = ["list", "form"].map((viewType) => {
                const view = views.find((view) => view[1] === viewType);
                return [view ? view[0] : false, viewType];
            });
            this.actionService.doAction({
                type: "ir.actions.act_window",
                name: actionTitle,
                res_model: resModel,
                views: openRecordsViews,
                domain,
                context,
                help: this._getNoContentHelper(),
            });
        }
    }

    /** Return grid cell action helper when no records are found. */
    _getNoContentHelper() {
        const noActivitiesFound = _t("No activities found");
        return  markup(
            `<p class='o_view_nocontent_smiling_face'>${escape(noActivitiesFound)}</p>`
        );
    }

    onMagnifierGlassClick(section, column) {
        const title = `${section.title} (${column.title})`;
        const domain = Domain.and([section.domain, column.domain]).toList();
        this.openRecords(title, domain, section.context);
    }

    get rangesArray() {
        return Object.values(this.props.ranges);
    }

    async onRangeClick(name) {
        await this.props.model.setRange(name);
        this.props.state.activeRangeName = name;
        this.shouldFocusOnToday = true;
    }

    async onTodayButtonClick() {
        await this.props.model.setTodayAnchor();
        this.shouldFocusOnToday = true;
    }

    async onPreviousButtonClick() {
        await this.props.model.moveAnchor("backward");
        this.shouldFocusOnToday = true;
    }

    async onNextButtonClick() {
        await this.props.model.moveAnchor("forward");
        this.shouldFocusOnToday = true;
    }
}
