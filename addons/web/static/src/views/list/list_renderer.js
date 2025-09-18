// @ts-check

/** @module @web/views/list/list_renderer - Table rendering, inline editing, column resize, and drag-and-drop for list view */

import {
    Component,
    onMounted,
    onPatched,
    onWillDestroy,
    onWillPatch,
    onWillRender,
    status,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { CheckBox } from "@web/components/checkbox/checkbox";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { Pager } from "@web/components/pager/pager";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { getClassNameFromDecoration } from "@web/core/utils/decorations";
import { useSortable } from "@web/core/utils/dnd/sortable_owl";
import { useBus, useService } from "@web/core/utils/hooks";
import { Field } from "@web/fields/field";
import { getTooltipInfo } from "@web/fields/field_tooltip";
import { MOVABLE_RECORD_TYPES } from "@web/model/relational_model/dynamic_group_list";
import { getActiveHotkey } from "@web/services/hotkeys/hotkey_service";
import { ActionHelper } from "@web/views/action_helper";
import { ViewButton } from "@web/views/view_button/view_button";
import { GroupConfigMenu } from "@web/views/view_components/group_config_menu";
import { useBounceButton } from "@web/views/view_hook";
import { getFormattedValue } from "@web/views/view_utils";
import { Widget } from "@web/views/widgets/widget";

import { useMagicColumnWidths } from "./column_width_hook";
import { useListAggregates } from "./list_aggregates";
import { ListAggregatesRow } from "./list_aggregates_row";
import {
    getPropertyFieldColumns as getPropertyFieldColumnsUtil,
    processAllColumns,
} from "./list_column_utils";
import { ListGridState } from "./list_grid_state";
import {
    countRecordsInGroup,
    getAggregateColumns as getAggregateColumnsUtil,
    getFirstAggregateIndex as getFirstAggregateIndexUtil,
    getGroupNameCellColSpan as getGroupNameCellColSpanUtil,
    getGroupPagerCellColspan as getGroupPagerCellColspanUtil,
    getLastAggregateIndex as getLastAggregateIndexUtil,
} from "./list_group_layout";
import { containsActiveElement, useListKeyboardNavigation } from "./list_keyboard_nav";
import { useListOptionalFields } from "./list_optional_fields";
import { useListSelection } from "./list_selection";
import { useListVirtualization } from "./list_virtualization";

/**
 * @typedef {import('@web/model/relational_model/dynamic_list').DynamicList} DynamicList
 * @typedef {import('@web/model/relational_model/group').Group} Group
 * @typedef {import('@web/model/relational_model/record').RelationalRecord} RelationalRecord
 * @typedef {import('@web/model/relational_model/relational_model').RelationalModel} RelationalModel
 * @typedef {import('@web/model/relational_model/static_list').StaticList} StaticList
 * @typedef {import("../view").ViewProps} ViewProps
 *
 * @typedef {{
 *  name: string;
 *  type: string;
 *  attrs: Record<string, string>;
 *  [key: string]: unknown;
 * }} Column
 *
 * @typedef {"up" | "down" | "left" | "right"} Direction
 *
 * @typedef {ViewProps & {
 *  list: DynamicList | StaticList;
 *  archInfo?: any;
 *  editable?: any;
 *  cycleOnTab?: boolean;
 *  allowSelectors?: boolean;
 *  [key: string]: any;
 * }} ListRendererProps
 */

const FIELD_CLASSES = {
    char: "o_list_char",
    float: "o_list_number",
    integer: "o_list_number",
    monetary: "o_list_number",
    text: "o_list_text",
    many2one: "o_list_many2one",
};

/** @extends Component */
export class ListRenderer extends Component {
    static template = "web.ListRenderer";
    static rowsTemplate = "web.ListRenderer.Rows";
    static recordRowTemplate = "web.ListRenderer.RecordRow";
    static groupRowTemplate = "web.ListRenderer.GroupRow";
    static useMagicColumnWidths = true;
    static LONG_TOUCH_THRESHOLD = 400;
    /** Minimum flat row count to activate row virtualization. Set Infinity to disable. */
    static VIRTUALIZATION_THRESHOLD = 100;
    static components = {
        DropdownItem,
        Field,
        ViewButton,
        CheckBox,
        Dropdown,
        Pager,
        Widget,
        ActionHelper,
        GroupConfigMenu,
        ListAggregatesRow,
    };
    static defaultProps = { allowSelectors: false, cycleOnTab: true };

    static props = [
        "activeActions?",
        "list",
        "archInfo",
        "openRecord",
        "onAdd?",
        "cycleOnTab?",
        "allowSelectors?",
        "editable?",
        "onOpenFormView?",
        "hasOpenFormViewButton?",
        "noContentHelp?",
        "nestedKeyOptionalFieldsData?",
        "optionalActiveFields?",
        "readonly?",
    ];

    setup() {
        this.actionService = useService("action");
        this.uiService = useService("ui");
        this.notificationService = useService("notification");
        this.orm = useService("orm");
        const key = this.createViewKey();
        this.keyOptionalFields = `optional_fields,${key}`;
        this.keyDebugOpenView = `debug_open_view,${key}`;
        this.cellClassByColumn = {};
        this.groupByButtons = this.props.archInfo.groupBy.buttons;
        useExternalListener(
            document,
            "click",
            /** @type {EventListener} */ (this.onGlobalClick.bind(this)),
        );
        this.tableRef = useRef("table");

        this.sel = useListSelection({
            getProps: () => this.props,
            getAllowSelectors: () => this.props.allowSelectors,
            toggleRecordSelection: (record) => this.toggleRecordSelection(record),
            longTouchThreshold: /** @type {any} */ (this.constructor)
                .LONG_TOUCH_THRESHOLD,
            getEnv: () => this.env,
        });

        /**
         * When resizing columns, it's possible that the pointer is not above the resize
         * handle (by some few pixel difference). During this scenario, click event
         * will be triggered on the column title which will reorder the column.
         * Column resize that triggers a reorder is not a good UX and we prevent this
         * using the following state variables: `resizing` and `preventReorder` which
         * are set during the column's click (onClickSortColumn), pointerup
         * (onColumnTitleMouseUp) and onStartResize events.
         */
        this.preventReorder = false;

        this.controls = this.props.archInfo.controls.length
            ? this.props.archInfo.controls
            : [{ type: "create", string: _t("Add a line") }];
        this.deleteControl =
            this.controls.find((control) => control.type === "delete") || {};

        this.nav = useListKeyboardNavigation(/** @type {any} */ (this.tableRef), {
            getColumns: () => this.columns,
            getEditedRecord: () => this.editedRecord,
            getProps: () => this.props,
            getEnv: () => this.env,
            getGridState: () => this.gridState,
            onToggleGroup: (group) => this.toggleGroup(group),
            onToggleRecordSelection: (record) => this.toggleRecordSelection(record),
            onAdd: (params) => this.add(params),
            onOpenRecord: (record) => this.props.openRecord(record),
            onDeleteRecord: (record) => this.onDeleteRecord(record),
            onEditNextRecord: (record, group) => this.editNextRecord(record, group),
            isInlineEditable: (record) => this.isInlineEditable(record),
            isCellReadonly: (column, record) => this.isCellReadonly(column, record),
            expandCheckboxes: (record, direction) =>
                this.sel.expandCheckboxes(
                    record,
                    /** @type {"up" | "down"} */ (direction),
                ),
            getCanCreate: () => this.canCreate,
            getDisplayRowCreates: () => this.displayRowCreates,
            getControls: () => this.controls,
            getSel: () => this.sel,
            getVirtualization: () => this.virt,
        });

        this.activeRowId = null;
        onMounted(async () => {
            // Due to the way elements are mounted in the DOM by Owl (bottom-to-top),
            // we need to wait the next micro task tick to set the activeElement.
            await Promise.resolve();
            this.activeElement = this.uiService.activeElement;
        });
        onWillPatch(() => {
            const activeRow = /** @type {HTMLElement | null} */ (
                document.activeElement?.closest(".o_data_row.o_selected_row")
            );
            this.activeRowId = activeRow ? activeRow.dataset.id : null;
        });
        this.opt = useListOptionalFields(
            this.keyOptionalFields,
            this.keyDebugOpenView,
            {
                getAllColumns: () => this.allColumns,
                getOptionalActiveFields: () => this.optionalActiveFields,
                onSave: () => this.saveOptionalActiveFields(),
            },
        );
        // useState makes optionalActiveFields reactive so ListAggregatesRow can
        // subscribe to property-level mutations (optional column toggle).
        this.optionalActiveFields = useState(this.props.optionalActiveFields || {});
        /** @type {Column[]} */
        this.allColumns = [];
        /** @type {Column[]} */
        this.columns = [];
        this.editedRecord = null;
        this.agg = useListAggregates({
            getColumns: () => this.columns,
            getFields: () => this.fields,
            getProps: () => this.props,
            getOptionalActiveFields: () => this.optionalActiveFields,
        });
        onWillRender(() => {
            this.editedRecord = this.props.list.editedRecord;

            performance.mark("list:processAllColumns:start");
            this.allColumns = /** @type {Column[]} */ (
                processAllColumns(this.props.archInfo.columns, this.props.list)
            );
            performance.measure(
                "list:processAllColumns",
                "list:processAllColumns:start",
            );

            Object.assign(
                this.optionalActiveFields,
                this.computeOptionalActiveFields(),
            );
            this.opt.refreshDebugOpenView();
            this.debugOpenView = this.opt.debugOpenView;

            performance.mark("list:getActiveColumns:start");
            this.columns = this.getActiveColumns();
            performance.measure("list:getActiveColumns", "list:getActiveColumns:start");

            this.withHandleColumn = this.columns.some((col) => col.widget === "handle");

            this.gridState.update({
                list: this.props.list,
                columns: this.columns,
                hasSelectors: this.hasSelectors,
                hasOpenFormViewColumn: this.hasOpenFormViewColumn,
                hasActionsColumn: this.hasActionsColumn,
                showAddLine: Boolean(this.props.editable && this.canCreate),
            });
            performance.mark("list:gridState.rebuild:start");
            this.gridState.rebuild();
            performance.measure(
                "list:gridState.rebuild",
                "list:gridState.rebuild:start",
            );

            performance.mark("list:virt.refresh:start");
            this.virt.refresh();
            performance.measure("list:virt.refresh", "list:virt.refresh:start");
        });
        this.state = useState({ showGroupInput: false });
        let dataRowId;
        let dataGroupId;
        this.rootRef = useRef("root");
        this.resequencePromise = Promise.resolve();
        useSortable({
            enable: () => this.canResequenceRows,
            // Params
            ref: this.rootRef,
            elements: ".o_row_draggable",
            handle: ".o_handle_cell",
            cursor: "grabbing",
            placeholderClasses: ["d-table-row"],
            // Hooks
            onDragStart: (params) => {
                const { element } = params;
                dataRowId = element.dataset.id;
                dataGroupId = this.props.list.isGrouped && element.dataset.groupId;
                return this.sortStart(params);
            },
            onDragEnd: (params) => this.sortStop(params),
            onDrop: (params) => this.sortDrop(dataRowId, dataGroupId, params),
        });

        useBounceButton(this.rootRef, () => this.showNoContentHelper);

        let isSmall = this.uiService.isSmall;
        useBus(this.uiService.bus, "resize", () => {
            if (isSmall !== this.uiService.isSmall) {
                isSmall = this.uiService.isSmall;
                this.render();
            }
        });

        this.columnWidths = useMagicColumnWidths(this.tableRef, () => ({
            columns: this.columns,
            isEmpty:
                !this.props.list.records.length || this.props.list.model.useSampleModel,
            hasSelectors: this.hasSelectors,
            hasOpenFormViewColumn: this.hasOpenFormViewColumn,
            hasActionsColumn: this.hasActionsColumn,
        }));

        onPatched(async () => {
            // HACK: we need to wait for the next tick to be sure that the Field components are patched.
            // OWL don't wait the patch for the children components if the children trigger a patch by himself.
            await Promise.resolve();
            if (status(this) === "destroyed") {
                return;
            }
            if (this.activeElement !== this.uiService.activeElement) {
                return;
            }
            if (this.editedRecord && this.activeRowId !== this.editedRecord.id) {
                if (
                    this.nav.cellToFocus &&
                    this.nav.cellToFocus.record === this.editedRecord
                ) {
                    const column = this.nav.cellToFocus.column;
                    const forward = this.nav.cellToFocus.forward;
                    this.focusCell(column, forward);
                } else {
                    const column = this.nav.lastEditedCell?.column || this.columns[0];
                    if (
                        column.widget !== "daterange" ||
                        !this.editedRecord.data[column.name]
                    ) {
                        this.focusCell(column);
                    }
                }
            }
            this.nav.cellToFocus = null;
            this.nav.lastEditedCell = null;
            /** @type {any} */ (this.nav).resolvePendingVirtFocus();
        });
        this.isRTL = localization.direction === "rtl";

        this.gridState = new ListGridState({
            list: this.props.list,
            columns: this.columns,
            hasSelectors: this.hasSelectors,
            hasOpenFormViewColumn: this.hasOpenFormViewColumn,
            hasActionsColumn: this.hasActionsColumn,
            isRTL: this.isRTL,
            showAddLine: Boolean(this.props.editable && this.canCreate),
            isCellReadonly: (col, rec) => this.isCellReadonly(col, rec),
        });

        this.virt = useListVirtualization({
            rootRef: this.rootRef,
            getGridState: () => this.gridState,
            getNbCols: () => this.nbCols,
            canResequence: () => this.canResequenceRows,
            getEditedRecord: () => this.editedRecord,
            threshold: /** @type {any} */ (this.constructor).VIRTUALIZATION_THRESHOLD,
        });

        this.dialogClose = [];
        onWillDestroy(() => {
            this.dialogClose.forEach((close) => close());
        });
    }

    displaySaveNotification() {
        this.notificationService.add(_t("Please save your changes first"), {
            type: "danger",
        });
    }

    getActiveColumns() {
        return this.allColumns.filter((col) => {
            if (col.optional && !this.optionalActiveFields[col.name]) {
                return false;
            }
            if (this.evalColumnInvisible(col.column_invisible)) {
                return false;
            }
            return true;
        });
    }

    get hasSelectors() {
        return this.props.allowSelectors && !this.env.isSmall;
    }

    get hasOpenFormViewColumn() {
        return this.props.hasOpenFormViewButton || this.debugOpenView;
    }

    get hasOptionalOpenFormViewColumn() {
        return (
            this.props.editable && this.env.debug && !this.props.hasOpenFormViewButton
        );
    }

    get hasActionsColumn() {
        return !!(
            this.displayOptionalFields ||
            this.activeActions.onDelete ||
            this.hasOptionalOpenFormViewColumn ||
            // spare some space to display the cog icon in group headers
            this.props.list.isGrouped
        );
    }

    add(params) {
        if (this.canCreate) {
            this.props.onAdd(params);
        }
    }

    /**
     * @param {Group} group
     */
    async addInGroup(group) {
        const left = await this.props.list.leaveEditMode({ canAbandon: false });
        if (left) {
            group.addNewRecord({}, this.props.editable === "top");
        }
    }

    /**
     * @param {Column} column
     * @param {DynamicList | StaticList} list
     */
    getPropertyFieldColumns(column, list) {
        return getPropertyFieldColumnsUtil(/** @type {any} */ (column), list);
    }

    /**
     * @param {RelationalRecord} record
     * @param {Column} column
     */
    getFieldProps(record, column) {
        return {
            readonly:
                this.props.readonly ||
                this.isCellReadonly(column, record) ||
                this.isRecordReadonly(record) ||
                (column.widget === "handle" && !this.canResequenceRows),
        };
    }

    get activeActions() {
        return this.props.activeActions || {};
    }

    get canCreateGroup() {
        const { archInfo, list, readonly } = this.props;
        const { activeActions, defaultGroupBy } = archInfo;
        return (
            !readonly &&
            activeActions.createGroup &&
            list.groupByField?.type === "many2one" &&
            list.groupByField.name === defaultGroupBy?.[0]
        );
    }

    get canResequenceRows() {
        if (!this.props.list.canResequence() || this.props.readonly) {
            return false;
        }
        const { groupBy, groupByField, handleField, orderBy } = this.props.list;
        if (
            groupBy?.length > 1 ||
            (groupByField && !MOVABLE_RECORD_TYPES.includes(groupByField.type))
        ) {
            return false;
        }
        return !orderBy.length || (orderBy.length && orderBy[0].name === handleField);
    }

    get fields() {
        return this.props.list.fields;
    }

    get nbCols() {
        let nbCols = this.columns.length;
        if (this.hasSelectors) {
            nbCols++;
        }
        if (this.hasActionsColumn) {
            nbCols++;
        }
        if (this.hasOpenFormViewColumn) {
            nbCols++;
        }
        return nbCols;
    }

    /**
     * @param {Column} column
     * @param {RelationalRecord} record
     */
    canUseFormatter(column, record) {
        if (column.widget) {
            return false;
        }
        if (
            record.isInEdition &&
            (record.model.multiEdit || this.isInlineEditable(record))
        ) {
            // in a x2many non editable list, a record is in edition when it is opened in a dialog,
            // but in the list we want it to still be displayed in readonly.
            return false;
        }
        return true;
    }

    /**
     * @param {RelationalRecord} record
     */
    isRecordReadonly(record) {
        if (record.isNew) {
            return false;
        }
        if (this.props.activeActions?.edit === false) {
            return true;
        }
        if (
            record.isInEdition &&
            !this.isInlineEditable(record) &&
            !record.model.multiEdit
        ) {
            // in a x2many non editable list, a record is in edition when it is opened in a dialog,
            // but in the list we want it to still be displayed in readonly.
            return true;
        }
        return false;
    }

    focusCell(column, forward = true) {
        this.nav.focusCell(column, forward);
    }

    /**
     * @param {HTMLElement} el
     */
    focus(el) {
        this.nav.focus(el);
    }

    editGroupRecord(group) {
        const { resId, resModel } = group.record;
        this.actionService.doAction({
            context: {
                create: false,
            },
            res_model: resModel,
            res_id: resId,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        });
    }

    createViewKey() {
        let keyParts = {
            fields: this.props.list.fieldNames, // FIXME: use something else?
            model: this.props.list.resModel,
            viewMode: "list",
            viewId: this.env.config.viewId,
        };

        if (this.props.nestedKeyOptionalFieldsData) {
            keyParts = Object.assign(keyParts, {
                model: this.props.nestedKeyOptionalFieldsData.model,
                viewMode: this.props.nestedKeyOptionalFieldsData.viewMode,
                relationalField: this.props.nestedKeyOptionalFieldsData.field,
                subViewType: "list",
            });
        }

        const parts = ["model", "viewMode", "viewId", "relationalField", "subViewType"];
        const viewIdentifier = [];
        parts.forEach((partName) => {
            if (partName in keyParts) {
                viewIdentifier.push(keyParts[partName]);
            }
        });
        keyParts.fields
            .sort((left, right) => (left < right ? -1 : 1))
            .forEach((fieldName) => viewIdentifier.push(fieldName));
        return viewIdentifier.join(",");
    }

    get optionalFieldGroups() {
        const propertyGroups = {};
        const optionalFields = [];
        const optionalColumns = this.allColumns.filter(
            (col) => col.optional && !this.evalColumnInvisible(col.column_invisible),
        );
        for (const col of optionalColumns) {
            const optionalField = {
                label: col.label,
                name: col.name,
                value: this.optionalActiveFields[col.name],
            };
            if (!col.relatedPropertyField) {
                optionalFields.push(optionalField);
            } else {
                const { displayName, id } = /** @type {any} */ (
                    col.relatedPropertyField
                );
                if (propertyGroups[id]) {
                    propertyGroups[id].optionalFields.push(optionalField);
                } else {
                    propertyGroups[id] = {
                        id,
                        displayName,
                        optionalFields: [optionalField],
                    };
                }
            }
        }
        if (optionalFields.length) {
            return [{ optionalFields }, ...Object.values(propertyGroups)];
        }
        return Object.values(propertyGroups);
    }

    get hasOptionalFields() {
        return this.allColumns.some(
            (col) => col.optional && !this.evalColumnInvisible(col.column_invisible),
        );
    }

    get displayOptionalFields() {
        return this.hasOptionalFields;
    }

    nbRecordsInGroup(group) {
        return countRecordsInGroup(group);
    }
    get selectAll() {
        const list = this.props.list;
        const nbDisplayedRecords = list.records.length;
        if (list.isDomainSelected) {
            return true;
        } else {
            return (
                nbDisplayedRecords > 0 && list.selection.length === nbDisplayedRecords
            );
        }
    }

    getGroupConfigMenuProps(group) {
        return {
            activeActions: this.props.activeActions,
            configItems: registry.category("group_config_items").getEntries(),
            deleteGroup: async () => await this.props.list.deleteGroups([group]),
            dialogClose: this.dialogClose,
            group,
            list: this.props.list,
        };
    }

    formatGroupAggregate(group, column) {
        return this.agg.formatGroupAggregate(group, column);
    }

    getGroupLevel(group) {
        return this.props.list.groupBy.length - group.list.groupBy.length - 1;
    }

    getColumnClass(column) {
        const classNames = ["align-middle"];
        if (this.isSortable(column)) {
            classNames.push("o_column_sortable", "position-relative", "cursor-pointer");
        } else {
            classNames.push("cursor-default");
        }
        const orderBy = this.props.list.orderBy;
        if (
            orderBy.length &&
            column.widget !== "handle" &&
            orderBy[0].name === column.name &&
            column.hasLabel
        ) {
            classNames.push("table-active");
        }
        if (this.isNumericColumn(column)) {
            classNames.push("o_list_number_th");
        }
        if (column.type === "button_group") {
            classNames.push("o_list_button");
        }
        if (column.widget) {
            classNames.push(`o_${column.widget}_cell`);
        }

        return classNames.join(" ");
    }

    /**
     *
     * @param {RelationalRecord} _record
     */
    getColumns(_record) {
        return this.columns;
    }

    isNumericColumn(column) {
        const { type } = this.fields[column.name];
        return ["float", "integer", "monetary"].includes(type);
    }

    isSortable(column) {
        const { hasLabel, name, options } = column;
        const { sortable } = this.fields[name];
        return (sortable || options.allow_order) && hasLabel;
    }

    getSortableIconClass(column) {
        const { orderBy } = this.props.list;
        const classNames = this.isSortable(column) ? ["fa"] : ["d-none"];
        if (orderBy.length && orderBy[0].name === column.name) {
            classNames.push(orderBy[0].asc ? "fa-sort-asc" : "fa-sort-desc");
        } else {
            classNames.push("fa-sort", "opacity-0", "opacity-100-hover");
        }

        return classNames.join(" ");
    }

    /**
     * Returns the classnames to apply to the row representing the given record.
     * @param {RelationalRecord} record
     */
    getRowClass(record) {
        /**
         * Classnames coming from decorations
         * @type {string[]}
         */
        const classNames = this.props.archInfo.decorations
            .filter((decoration) =>
                evaluateBooleanExpr(
                    decoration.condition,
                    record.evalContextWithVirtualIds,
                ),
            )
            .map((decoration) => decoration.class);
        if (record.selected) {
            classNames.push("table-info");
        }
        // "o_selected_row" classname for the potential row in edition
        if (record.isInEdition) {
            classNames.push("o_selected_row");
        }
        if (record.selected) {
            classNames.push("o_data_row_selected");
        }
        if (this.canResequenceRows) {
            classNames.push("o_row_draggable");
        }
        return classNames.join(" ");
    }

    /**
     * @param {Column} column
     * @param {RelationalRecord} record
     */
    getCellClass(column, record) {
        if (column.relatedPropertyField && !(column.name in record.data)) {
            return "";
        }

        if (!this.cellClassByColumn[column.id]) {
            const classNames = ["o_data_cell"];
            if (column.type === "button_group") {
                classNames.push("o_list_button");
            } else if (column.type === "field") {
                classNames.push("o_field_cell");
                if (
                    column.attrs &&
                    column.attrs.class &&
                    this.canUseFormatter(column, record)
                ) {
                    classNames.push(column.attrs.class);
                }
                const typeClass = FIELD_CLASSES[this.fields[column.name].type];
                if (typeClass) {
                    classNames.push(typeClass);
                }
                if (column.widget) {
                    classNames.push(`o_${column.widget}_cell`);
                }
            }
            this.cellClassByColumn[column.id] = classNames;
        }
        const classNames = [...this.cellClassByColumn[column.id]];
        if (column.type === "field") {
            if (
                evaluateBooleanExpr(
                    /** @type {any} */ (column.required),
                    record.evalContextWithVirtualIds,
                )
            ) {
                classNames.push("o_required_modifier");
            }
            if (record.isFieldInvalid(column.name)) {
                classNames.push("o_invalid_cell");
            }
            if (this.isCellReadonly(column, record)) {
                classNames.push("o_readonly_modifier");
            }
            if (this.canUseFormatter(column, record)) {
                // generate field decorations classNames (only if field-specific decorations
                // have been defined in an attribute, e.g. decoration-danger="other_field = 5")
                // only handle the text-decoration.
                const decorations = /** @type {Record<string, string>} */ (
                    column.decorations
                );
                for (const decoName in decorations) {
                    if (
                        evaluateBooleanExpr(
                            decorations[decoName],
                            record.evalContextWithVirtualIds,
                        )
                    ) {
                        classNames.push(getClassNameFromDecoration(decoName));
                    }
                }
            }
            if (
                record.isInEdition &&
                this.editedRecord &&
                this.isCellReadonly(column, this.editedRecord)
            ) {
                classNames.push("text-muted");
            } else {
                classNames.push("cursor-pointer");
            }
        }
        return classNames.join(" ");
    }

    /**
     * @param {Column} column
     * @param {RelationalRecord} record
     */
    isCellReadonly(column, record) {
        return !!(
            this.isRecordReadonly(record) ||
            (column.relatedPropertyField &&
                record.selected &&
                record.model.multiEdit) ||
            evaluateBooleanExpr(
                /** @type {string} */ (column.readonly),
                record.evalContextWithVirtualIds,
            )
        );
    }

    /**
     * @param {Column} column
     * @param {RelationalRecord} record
     */
    getCellTitle(column, record) {
        // Because we freeze the column sizes, it may happen that we have to shorten field values.
        // In order for the user to have access to the complete value in those situations, we put
        // the value as title of the cells.
        if (["many2one", "reference", "char"].includes(this.fields[column.name].type)) {
            return this.getFormattedValue(column, record);
        }
    }

    getFieldClass(column) {
        return column.attrs && column.attrs.class;
    }

    /**
     * @param {Column} column
     * @param {RelationalRecord} record
     */
    getFormattedValue(column, record) {
        const fieldName = column.name;
        if (/** @type {any} */ (column.options)?.enable_formatting === false) {
            const value = record.data[fieldName];
            return value === false ? "" : value;
        }
        return getFormattedValue(record, fieldName, column);
    }

    /**
     * @param {string} invisible
     * @param {RelationalRecord} record
     */
    evalInvisible(invisible, record) {
        return evaluateBooleanExpr(invisible, record.evalContextWithVirtualIds);
    }

    evalColumnInvisible(columnInvisible) {
        return evaluateBooleanExpr(columnInvisible, this.props.list.evalContext);
    }

    get canCreate() {
        return "link" in this.activeActions
            ? this.activeActions.link
            : this.activeActions.create;
    }

    get isX2Many() {
        return this.activeActions.type !== "view";
    }

    get getEmptyRowIds() {
        let nbEmptyRow = Math.max(0, 4 - this.props.list.records.length);
        if (nbEmptyRow > 0 && this.displayRowCreates) {
            nbEmptyRow -= 1;
        }
        return Array.from({ length: nbEmptyRow }, (_, i) => i);
    }

    get displayRowCreates() {
        return this.isX2Many && this.canCreate;
    }

    /**
     * @param {RelationalRecord} record
     */
    displayDeleteIcon(record) {
        return !evaluateBooleanExpr(this.deleteControl.invisible, record.evalContext);
    }

    // Group headers logic:
    // if there are aggregates, the first th spans until the first
    // aggregate column then all cells between aggregates are rendered
    // a single cell is rendered after the last aggregated column to render the
    // pager (with adequate colspan)
    // ex:
    // TH TH TH TH TH AGG AGG TH AGG AGG TH TH TH
    // 0  1  2  3  4   5   6   7  8   9  10 11 12
    // [    TH 5    ][TH][TH][TH][TH][TH][ TH 3 ]
    // [ group name ][ aggregate cells  ][ pager]
    getFirstAggregateIndex(group) {
        const aggregates = group
            ? group.aggregates
            : /** @type {any} */ (this).aggregates;
        return getFirstAggregateIndexUtil(
            /** @type {any} */ (this.columns),
            this.fields,
            aggregates,
        );
    }
    getLastAggregateIndex(group) {
        const aggregates = group
            ? group.aggregates
            : /** @type {any} */ (this).aggregates;
        return getLastAggregateIndexUtil(
            /** @type {any} */ (this.columns),
            this.fields,
            aggregates,
        );
    }
    getAggregateColumns(group) {
        const aggregates = group
            ? group.aggregates
            : /** @type {any} */ (this).aggregates;
        return getAggregateColumnsUtil(
            /** @type {any} */ (this.columns),
            this.fields,
            aggregates,
        );
    }
    getGroupNameCellColSpan(group) {
        const aggregates = group
            ? group.aggregates
            : /** @type {any} */ (this).aggregates;
        return getGroupNameCellColSpanUtil(
            /** @type {any} */ (this.columns),
            this.fields,
            aggregates,
            {
                hasSelectors: this.hasSelectors,
            },
        );
    }

    getGroupPagerCellColspan(group) {
        const aggregates = group
            ? group.aggregates
            : /** @type {any} */ (this).aggregates;
        return getGroupPagerCellColspanUtil(
            /** @type {any} */ (this.columns),
            this.fields,
            aggregates,
            {
                hasOpenFormViewColumn: this.hasOpenFormViewColumn,
            },
        );
    }

    getGroupPagerProps(group) {
        const list = group.list;
        return {
            offset: list.offset,
            limit: list.limit,
            total: list.count,
            onUpdate: async ({ offset, limit }) => {
                await list.load({ limit, offset });
                this.render(true);
            },
            withAccessKey: false,
        };
    }

    computeOptionalActiveFields() {
        return this.opt.computeOptionalActiveFields();
    }

    onClickSortColumn(column) {
        if (this.preventReorder) {
            this.preventReorder = false;
            return;
        }
        if (this.editedRecord || this.props.list.model.useSampleModel) {
            return;
        }
        const fieldName = column.name;
        const list = this.props.list;
        if (this.isSortable(column)) {
            list.sortBy(fieldName);
        }
    }

    /**
     * @param {RelationalRecord} record
     * @param {Column} column
     * @param {PointerEvent} ev
     */
    onButtonCellClicked(record, column, ev) {
        if (!(/** @type {HTMLElement} */ (ev.target).closest("button"))) {
            this.onCellClicked(record, column, ev);
        }
    }

    /**
     * @param {RelationalRecord} record
     * @param {Column} column
     * @param {PointerEvent} ev
     */
    async onCellClicked(record, column, ev, newWindow) {
        if (/** @type {any} */ (ev.target).special_click) {
            return;
        }

        const multiEdit = this.props.list.model.multiEdit;
        const hasSelection = !!this.props.list.selection.length;
        if (hasSelection && this.canSelectRecord && (!multiEdit || !record.selected)) {
            this.toggleRecordSelection(record);
        } else if (
            (multiEdit && record.selected) ||
            (this.isInlineEditable(record) && !hasSelection)
        ) {
            if (record.isInEdition && this.editedRecord === record) {
                const cell = this.tableRef.el.querySelector(
                    `.o_selected_row td[name='${column.name}']`,
                );
                if (cell && containsActiveElement(cell)) {
                    this.nav.lastEditedCell = { column, record };
                    // Cell is already focused.
                    return;
                }
                this.focusCell(column);
                this.nav.cellToFocus = null;
            } else {
                const recordIndex = this.props.list.records.indexOf(record);
                await this.resequencePromise;
                // row might have changed record after resequence
                record = this.props.list.records[recordIndex] || record;
                await this.props.list.enterEditMode(record);
                this.nav.cellToFocus = { column, record };
                if (
                    column.type === "field" &&
                    record.fields[column.name].type === "boolean" &&
                    (!column.widget || column.widget === "boolean")
                ) {
                    if (
                        !this.isCellReadonly(column, record) &&
                        !this.evalInvisible(
                            /** @type {string} */ (column.invisible),
                            record,
                        )
                    ) {
                        await record.update({
                            [column.name]: !record.data[column.name],
                        });
                    }
                }
            }
        } else if (this.editedRecord && this.editedRecord !== record) {
            this.props.list.leaveEditMode();
        } else if (!this.props.archInfo.noOpen) {
            this.props.openRecord(record, { newWindow });
        }
    }

    /**
     * @param {RelationalRecord} record
     * @param {PointerEvent} ev
     */
    async onRemoveCellClicked(record, ev) {
        const element = /** @type {HTMLElement} */ (
            /** @type {HTMLElement} */ (ev.target).closest(".o_list_record_remove")
        );
        if (element.dataset.clicked) {
            return;
        }
        element.dataset.clicked = "true";
        try {
            await this.onDeleteRecord(record);
        } finally {
            delete element.dataset.clicked;
        }
    }

    openMultiCurrencyPopover(ev, value, fieldName) {
        this.agg.openMultiCurrencyPopover(ev, value, fieldName);
    }

    /**
     * @param {RelationalRecord} record
     */
    async onDeleteRecord(record) {
        if (this.editedRecord && this.editedRecord !== record) {
            const left = await this.props.list.leaveEditMode();
            if (!left) {
                return;
            }
        }
        if (this.activeActions.onDelete) {
            return this.activeActions.onDelete(record);
        }
    }

    /**
     * @param {HTMLTableCellElement} cell
     * @param {boolean} cellIsInGroupRow
     * @param {Direction} direction
     */
    findFocusFutureCell(cell, cellIsInGroupRow, direction) {
        return this.nav.findFocusFutureCell(cell, cellIsInGroupRow, direction);
    }

    /**
     * @param {RelationalRecord} _record
     */
    isInlineEditable(_record) {
        // /!\ the keyboard navigation works under the hypothesis that all or
        // none records are editable.
        return !!this.props.editable;
    }

    /**
     * @param {KeyboardEvent} ev
     * @param {Group | null} group
     * @param {RelationalRecord | null} record
     */
    onCellKeydown(ev, group = null, record = null) {
        if (this.props.list.model.useSampleModel) {
            return;
        }

        const hotkey = getActiveHotkey(ev);

        if (
            /** @type {HTMLElement} */ (ev.target).tagName === "TEXTAREA" &&
            hotkey === "enter"
        ) {
            return;
        }

        const closestCell = /** @type {HTMLTableCellElement} */ (
            /** @type {HTMLElement} */ (ev.target).closest("td, th")
        );

        if (this.nav.toggleFocusInsideCell(hotkey, closestCell)) {
            return;
        }

        const handled = this.editedRecord
            ? this.onCellKeydownEditMode(hotkey, closestCell, group, record)
            : this.onCellKeydownReadOnlyMode(hotkey, closestCell, group, record); // record is supposed to be not null here

        if (handled) {
            this.lastCreatingAction = false;
            for (const tbody of this.tableRef.el.getElementsByTagName("tbody")) {
                tbody.classList.add("o_keyboard_navigation");
            }
            ev.preventDefault();
            ev.stopPropagation();
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    /**
     * Called by ListAggregatesRow when the user confirms a new group name.
     *
     * @param {string} value
     */
    addNewGroup(value) {
        this.state.showGroupInput = false;
        if (value) {
            this.props.list.createGroup(value);
        }
    }

    editNextRecord(record, group) {
        const list = this.props.list;
        const topReCreate = this.props.editable === "top" && record.isNew;
        const index = list.records.indexOf(record);
        let futureRecord = list.records[index + 1];
        if (topReCreate && index === 0) {
            futureRecord = null;
        }

        if (!futureRecord && !this.canCreate) {
            futureRecord = list.records[0];
        }

        if (futureRecord) {
            list.leaveEditMode({ validate: true }).then((canProceed) => {
                if (canProceed) {
                    list.enterEditMode(futureRecord);
                }
            });
        } else if (
            this.nav.lastIsDirty ||
            !record.canBeAbandoned ||
            this.displayRowCreates
        ) {
            this.add({ group });
        } else {
            futureRecord = list.records.at(0);
            list.enterEditMode(futureRecord);
        }
    }

    /**
     * @param {string} hotkey
     * @param {HTMLTableCellElement} cell
     * @param {Group | null} group
     * @param {RelationalRecord | null} record
     * @returns {boolean} true if some behavior has been taken
     */
    onCellKeydownEditMode(hotkey, cell, group, record) {
        return this.nav.onCellKeydownEditMode(hotkey, cell, group, record);
    }

    /**
     * @param {string} hotkey
     * @param {HTMLTableCellElement} cell
     * @param {Group | null} group
     * @param {RelationalRecord | null} record
     * @returns {boolean} true if some behavior has been taken
     */
    onCellKeydownReadOnlyMode(hotkey, cell, group, record) {
        return this.nav.onCellKeydownReadOnlyMode(hotkey, cell, group, record);
    }

    saveOptionalActiveFields() {
        this.opt.saveOptionalActiveFields();
    }

    get showNoContentHelper() {
        const { model } = this.props.list;
        return this.props.noContentHelp && (model.useSampleModel || !model.hasData());
    }

    /**
     * @param {Group} group
     */
    showGroupPager(group) {
        return !group.isFolded && group.list.limit < group.list.count;
    }

    /**
     * @param {Group} group
     */
    showGroupConfigMenu(group) {
        return (
            group.value && ["many2one", "many2many"].includes(group.groupByField.type)
        );
    }

    /**
     * @param {PointerEvent} _ev
     * @param {Group} group
     */
    async onGroupHeaderClicked(_ev, group) {
        const left = await this.props.list.leaveEditMode();
        if (left) {
            this.toggleGroup(group);
        }
    }

    /**
     * @param {Group} group
     */
    toggleGroup(group) {
        group.toggle();
    }

    get canSelectRecord() {
        return !this.editedRecord && !this.props.list.model.useSampleModel;
    }

    toggleSelection() {
        const list = this.props.list;
        if (!this.canSelectRecord) {
            return;
        }
        return list.toggleSelection();
    }

    /**
     * @param {RelationalRecord} record
     * @param {PointerEvent} [_ev]
     */
    toggleRecordSelection(record, _ev) {
        if (!this.canSelectRecord) {
            return;
        }
        const isRecordPresent = this.props.list.records.includes(
            this.sel.lastCheckedRecord,
        );
        if (this.sel.shiftKeyMode && isRecordPresent) {
            this.sel.toggleRangeSelection(record);
        } else {
            record.toggleSelection();
        }
        this.sel.lastCheckedRecord = record;
    }

    /**
     * @param {string} fieldName
     */
    async toggleOptionalField(fieldName) {
        this.opt.toggleOptionalField(fieldName, () => this.render());
    }

    /**
     * @param {string} groupId
     */
    toggleOptionalFieldGroup(groupId) {
        this.opt.toggleOptionalFieldGroup(groupId, () => this.render());
    }

    toggleDebugOpenView() {
        this.opt.toggleDebugOpenView(() => this.render());
        this.debugOpenView = this.opt.debugOpenView;
    }

    /**
     * @param {PointerEvent} ev
     */
    onGlobalClick(ev) {
        if (!(this.editedRecord || this.state.showGroupInput)) {
            return; // there's no row or group in edition
        }

        this.tableRef.el
            .querySelector("tbody")
            .classList.remove("o_keyboard_navigation");

        const target = /** @type {HTMLElement} */ (ev.target);
        // Close group input when the user clicks anywhere except the input itself.
        // The input now lives in ListAggregatesRow so we use CSS class instead of ref.
        if (this.state.showGroupInput && !target.closest(".o_list_group_input")) {
            this.state.showGroupInput = false;
        }
        if (this.tableRef.el.contains(target) && target.closest(".o_data_row")) {
            // ignore clicks inside the table that are originating from a record row
            // as they are handled directly by the renderer.
            return;
        }
        if (this.activeElement !== this.uiService.activeElement) {
            return;
        }
        // DateTime picker
        if (target.closest(".o_datetime_picker")) {
            return;
        }
        // Legacy autocomplete
        if (target.closest(".ui-autocomplete")) {
            return;
        }
        this.props.list.leaveEditMode();
    }

    get isDebugMode() {
        return Boolean(odoo.debug);
    }

    /**
     * @param {Column} column
     */
    makeTooltip(column) {
        return getTooltipInfo({
            viewMode: "list",
            resModel: this.props.list.resModel,
            field: this.fields[column.name],
            fieldInfo: column,
        });
    }

    onColumnTitleMouseUp() {
        if (this.columnWidths.resizing) {
            this.preventReorder = true;
        }
    }

    /**
     * @param {RelationalRecord} record
     * @param {TouchEvent} ev
     */
    onRowTouchStart(record, ev) {
        this.sel.onRowTouchStart(record, ev);
    }

    /**
     * @param {RelationalRecord} _record
     */
    onRowTouchEnd(_record) {
        this.sel.onRowTouchEnd(_record);
    }

    /**
     * @param {RelationalRecord} _record
     */
    onRowTouchMove(_record) {
        this.sel.onRowTouchMove(_record);
    }

    /**
     * @param {string} dataRowId
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} [params.group]
     * @param {HTMLElement} [params.next]
     * @param {HTMLElement} [params.parent]
     * @param {HTMLElement} [params.previous]
     */
    async sortDrop(dataRowId, dataGroupId, { element, previous }) {
        element.classList.remove("o_row_draggable");
        const refId = previous ? previous.dataset.id : null;
        try {
            if (dataGroupId) {
                this.resequencePromise = this.props.list.moveRecord(
                    dataRowId,
                    dataGroupId,
                    refId,
                    previous.dataset.groupId,
                );
            } else {
                this.resequencePromise = this.props.list.resequence(dataRowId, refId, {
                    handleField: this.props.list.handleField,
                });
            }
            await this.resequencePromise;
        } finally {
            element.classList.add("o_row_draggable");
            await this.props.list.leaveEditMode();
        }
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} [params.group]
     */
    sortStart({ element }) {
        const table = this.tableRef.el;
        const headers = [...table.querySelectorAll("thead th")];
        const cells = /** @type {HTMLTableCellElement[]} */ ([
            ...element.querySelectorAll("td"),
        ]);
        let headerIndex = 0;
        for (const cell of cells) {
            let width = 0;
            for (let i = 0; i < cell.colSpan; i++) {
                const header = headers[headerIndex + i];
                const style = getComputedStyle(header);
                width += parseFloat(style.width);
            }
            cell.style.width = `${width}px`;
            headerIndex += cell.colSpan;
        }
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} [params.group]
     */
    sortStop({ element }) {
        for (const cell of element.querySelectorAll("td")) {
            cell.style.width = null;
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    ignoreEventInSelectionMode(ev) {
        this.sel.ignoreEventInSelectionMode(ev);
    }

    /**
     * @param {RelationalRecord} record
     * @param {PointerEvent} ev
     */
    onClickCapture(record, ev) {
        this.sel.onClickCapture(record, ev);
    }
}
