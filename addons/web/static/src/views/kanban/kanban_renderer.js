/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { url } from "@web/core/utils/urls";
import { ColorPickerField } from "@web/fields/color_picker_field";
import { Field } from "@web/fields/field";
import { fileTypeMagicWordMap } from "@web/fields/image_field";
import { session } from "@web/session";
import { useViewCompiler } from "@web/views/helpers/view_compiler";
import { isRelational } from "@web/views/helpers/view_utils";
import { KanbanAnimatedNumber } from "@web/views/kanban/kanban_animated_number";
import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { useSortable } from "@web/views/kanban/kanban_sortable";
import { isAllowedDateField } from "@web/views/relational_model";
import { ViewButton } from "@web/views/view_button/view_button";
import { useBounceButton } from "@web/views/helpers/view_hook";
import { KanbanColumnQuickCreate } from "./kanban_column_quick_create";
import { KanbanRecordQuickCreate } from "./kanban_record_quick_create";

const { Component, useState, useRef } = owl;
const { RECORD_COLORS } = ColorPickerField;

const DRAGGABLE_GROUP_TYPES = ["many2one"];
const MOVABLE_RECORD_TYPES = ["char", "boolean", "integer", "selection", "many2one"];
const GLOBAL_CLICK_CANCEL_SELECTORS = ["a", ".dropdown", ".oe_kanban_action"];

const isBinSize = (value) => /^\d+(\.\d*)? [^0-9]+$/.test(value);
const isNull = (value) => [null, undefined].includes(value);

const formatterRegistry = registry.category("formatters");

export class KanbanRenderer extends Component {
    setup() {
        const { arch, cards, className, fields, xmlDoc, examples } = this.props.archInfo;
        this.cards = cards;
        this.className = className;
        this.cardTemplate = useViewCompiler(KanbanCompiler, arch, fields, xmlDoc);
        this.state = useState({
            columnQuickCreateIsFolded:
                !this.props.list.isGrouped || this.props.list.groups.length > 0,
        });
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.mousedownTarget = null;
        this.colors = RECORD_COLORS;
        this.exampleData = registry.category("kanban_examples").get(examples, null);
        this.ghostColumns = this.generateGhostColumns();
        // Sortable
        let dataRecordId;
        let dataGroupId;
        const rootRef = useRef("root");
        useSortable({
            ref: rootRef,
            setup: () =>
                this.canResequenceRecords && {
                    listSelector: this.props.list.isGrouped ? ".o_kanban_group" : false,
                    itemSelector: ".o_record_draggable",
                    containment: this.canMoveRecords ? false : "parent",
                    axis: !this.canMoveRecords && this.props.list.isGrouped ? "y" : false,
                    cursor: "move",
                },
            onListEnter(group) {
                group.classList.add("o_kanban_hover");
            },
            onListLeave(group) {
                group.classList.remove("o_kanban_hover");
            },
            onStart(group, item) {
                dataRecordId = item.dataset.id;
                if (group) {
                    dataGroupId = group.dataset.id;
                }
                item.classList.add("o_dragged");
            },
            onStop(group, item) {
                item.classList.remove("o_dragged");
            },
            onDrop: async ({ item, previous, parent }) => {
                item.classList.remove("o_record_draggable");
                const refId = previous ? previous.dataset.id : null;
                let targetGroupId;
                if (this.props.list.isGrouped) {
                    const groupEl = parent.closest(".o_kanban_group");
                    targetGroupId = groupEl.dataset.id;
                }
                await this.props.list.moveRecord(dataRecordId, dataGroupId, refId, targetGroupId);
                item.classList.add("o_record_draggable");
            },
        });
        useSortable({
            ref: rootRef,
            setup: () =>
                this.canResequenceGroups && {
                    itemSelector: ".o_group_draggable",
                    containment: "parent",
                    axis: "x",
                    handle: ".o_column_title",
                    cursor: "move",
                },
            onStart(group, item) {
                dataGroupId = item.dataset.id;
                item.classList.add("o_dragged");
            },
            onStop(group, item) {
                item.classList.remove("o_dragged");
            },
            onDrop: async ({ item, previous }) => {
                item.classList.remove("o_group_draggable");
                const refId = previous ? previous.dataset.id : null;
                await this.props.list.resequence(dataGroupId, refId);
                item.classList.add("o_group_draggable");
            },
        });
        useBounceButton(rootRef, (clickedEl) => {
            if (!this.props.list.count || this.props.list.model.useSampleModel) {
                return clickedEl.matches(
                    [
                        ".o_kanban_renderer",
                        ".o_kanban_group",
                        ".o_kanban_header",
                        ".o_column_quick_create",
                        ".o_view_nocontent_smiling_face",
                    ].join(", ")
                );
            }
            return false;
        });
    }

    // ------------------------------------------------------------------------
    // Getters
    // ------------------------------------------------------------------------

    getRawValue(record, fieldName) {
        const field = record.fields[fieldName];
        let value = record.data[fieldName];
        if (["one2many", "many2many"].includes(field.type)) {
            value = value.resIds;
        }
        return value;
    }

    getValue(record, fieldName) {
        const field = record.fields[fieldName];
        const formatter = formatterRegistry.get(field.type);
        return formatter(this.getRawValue(record, fieldName), { field });
    }

    get canMoveRecords() {
        if (!this.canResequenceRecords) {
            return false;
        }
        const { groupByField } = this.props.list;
        const { modifiers, type } = groupByField;
        return (
            !(modifiers && modifiers.readonly) &&
            (isAllowedDateField(groupByField) || MOVABLE_RECORD_TYPES.includes(type))
        );
    }

    get canResequenceGroups() {
        if (!this.props.list.isGrouped) {
            return false;
        }
        const { modifiers, type } = this.props.list.groupByField;
        return !(modifiers && modifiers.readonly) && DRAGGABLE_GROUP_TYPES.includes(type);
    }

    get canResequenceRecords() {
        return (
            (this.props.archInfo.hasHandleWidget || this.props.list.isGrouped) &&
            this.props.archInfo.recordsDraggable
        );
    }

    // `context` can be called in the evaluated kanban template.
    get context() {
        return this.props.context;
    }

    get showNoContentHelper() {
        const { model, isGrouped, groups } = this.props.list;
        if (model.useSampleModel) {
            return true;
        }
        if (isGrouped) {
            if (!this.state.columnQuickCreateIsFolded) {
                return false;
            }
            if (groups.length === 0) {
                return true;
            }
        }
        return !model.hasData();
    }

    /**
     * When the kanban records are grouped, the 'false' or 'undefined' group
     * must appear first.
     * @returns {any[]}
     */
    getGroupsOrRecords() {
        const { list } = this.props;
        if (list.isGrouped) {
            return list.groups
                .sort((a, b) => (a.value && !b.value ? 1 : !a.value && b.value ? -1 : 0))
                .map((group, i) => ({
                    group,
                    key: `group_key_${isNull(group.value) ? i : String(group.value)}`,
                }));
        } else {
            return list.records.map((record) => ({ record, key: record.resId }));
        }
    }

    getGroupName({ groupByField, count, displayName, isFolded }) {
        let name = displayName;
        if (isNull(name)) {
            name = this.env._t("None");
        } else if (isRelational(groupByField)) {
            name = name || this.env._t("None");
        } else if (groupByField.type === "boolean") {
            name = name ? this.env._t("Yes") : this.env._t("No");
        }
        return isFolded ? `${name} (${count})` : name;
    }

    getGroupClasses(group) {
        const classes = [];
        if (this.canResequenceGroups) {
            classes.push("o_group_draggable");
        }
        if (!group.count) {
            classes.push("o_kanban_no_records");
        }
        if (group.isFolded) {
            classes.push("o_column_folded");
        }
        if (group.progressValues.length) {
            classes.push("o_kanban_has_progressbar");
            if (!group.isFolded && group.hasActiveProgressValue) {
                const progressValue = group.progressValues.find(
                    (d) => d.value === group.activeProgressValue
                );
                classes.push("o_kanban_group_show", `o_kanban_group_show_${progressValue.color}`);
            }
        }
        return classes.join(" ");
    }

    getGroupUnloadedCount(group) {
        let total = group.count;
        if (group.hasActiveProgressValue) {
            const progressValue = group.progressValues.find(
                (d) => d.value === group.activeProgressValue
            );
            total = progressValue.count;
        }
        return total - group.list.records.length;
    }

    getRecordClasses(record, group) {
        const classes = ["o_kanban_record"];
        const { fieldName } = this.props.list.model.progressAttributes || {};
        if (group && record.data[fieldName]) {
            const value = record.data[fieldName];
            const progressValue = group.progressValues.find((p) => p.value === value);
            classes.push(`oe_kanban_card_${progressValue ? progressValue.color : "muted"}`);
        }
        if (this.canResequenceRecords) {
            classes.push("o_record_draggable");
        }
        if (this.props.list.model.useSampleModel) {
            classes.push("o_sample_data_disabled");
        }
        return classes.join(" ");
    }

    getGroupAggregate(group) {
        const { sumField } = this.props.list.model.progressAttributes;
        const value = group.getAggregates(sumField && sumField.name);
        const title = sumField ? sumField.string : this.env._t("Count");
        let currency = false;
        if (sumField && value && sumField.currency_field) {
            currency = session.currencies[session.company_currency_id];
        }
        return { value, currency, title };
    }

    generateGhostColumns() {
        let colNames;
        if (this.exampleData && this.exampleData.ghostColumns) {
            colNames = this.exampleData.ghostColumns;
        } else {
            colNames = [1, 2, 3, 4].map((num) => sprintf(this.env._t("Column %s"), num));
        }
        return colNames.map((colName) => ({
            name: colName,
            cards: new Array(Math.floor(Math.random() * 4) + 2),
        }));
    }

    // ------------------------------------------------------------------------
    // Permissions
    // ------------------------------------------------------------------------

    canArchiveGroup(group) {
        const { activeActions } = this.props.archInfo;
        const hasActiveField = "active" in group.fields;
        return activeActions.groupArchive && hasActiveField && !this.props.list.groupedBy("m2m");
    }

    canCreateGroup() {
        const { activeActions } = this.props.archInfo;
        return activeActions.groupCreate && this.props.list.groupedBy("m2o");
    }

    canDeleteGroup(group) {
        const { activeActions } = this.props.archInfo;
        const { groupByField } = this.props.list;
        return activeActions.groupDelete && isRelational(groupByField) && group.value;
    }

    canDeleteRecord() {
        const { activeActions } = this.props.archInfo;
        return activeActions.delete && !this.props.list.groupedBy("m2m");
    }

    canEditGroup(group) {
        const { activeActions } = this.props.archInfo;
        const { groupByField } = this.props.list;
        return activeActions.groupEdit && isRelational(groupByField) && group.value;
    }

    canEditRecord() {
        return this.props.archInfo.activeActions.edit;
    }

    // ------------------------------------------------------------------------
    // Edition methods
    // ------------------------------------------------------------------------

    quickCreate(group) {
        return this.props.list.quickCreate(group);
    }

    async validateQuickCreate(mode, group) {
        const record = await group.validateQuickCreate();
        if (mode === "edit") {
            await this.props.openRecord(record);
        } else {
            await this.quickCreate(group);
        }
    }

    toggleGroup(group) {
        group.toggle();
    }

    loadMore(group) {
        group.list.loadMore();
    }

    editGroup(group) {
        // TODO
        console.warn("TODO: Open group", group.id);
    }

    archiveGroup(group) {
        this.dialog.add(ConfirmationDialog, {
            body: this.env._t(
                "Are you sure that you want to archive all the records from this column?"
            ),
            confirm: () => group.list.archive(),
            cancel: () => {},
        });
    }

    unarchiveGroup(group) {
        group.list.unarchive();
    }

    deleteGroup(group) {
        this.dialog.add(ConfirmationDialog, {
            body: this.env._t("Are you sure you want to delete this column?"),
            confirm: async () => {
                await this.props.list.deleteGroups([group]);
                if (this.props.list.groups.length === 0) {
                    this.state.columnQuickCreateIsFolded = false;
                }
            },
            cancel: () => {},
        });
    }

    deleteRecord(record, group) {
        const listOrGroup = group || this.props.list;
        this.dialog.add(ConfirmationDialog, {
            body: this.env._t("Are you sure you want to delete this record?"),
            confirm: () => listOrGroup.deleteRecords([record]),
            cancel: () => {},
        });
    }

    selectColor(record, colorIndex) {
        // TODO
        console.warn("TODO: Update record", record.id, {
            [this.props.archInfo.colorField]: colorIndex,
        });
    }

    triggerAction(record, group, params) {
        const { type } = params;
        switch (type) {
            case "edit":
            case "open": {
                this.props.openRecord(record);
                break;
            }
            case "delete": {
                this.deleteRecord(record, group);
                break;
            }
            case "action":
            case "object": {
                // TODO
                console.warn("TODO: Button clicked for record", record.id, { params });
                break;
            }
            case "set_cover": {
                const { fieldName, widget, autoOpen } = params;
                const field = this.props.list.fields[fieldName];
                if (
                    field.type === "many2one" &&
                    field.relation === "ir.attachment" &&
                    widget === "attachment_image"
                ) {
                    // TODO
                    console.warn("TODO: Update record", record.id, { fieldName, autoOpen });
                } else {
                    const warning = sprintf(
                        this.env._t(
                            `Could not set the cover image: incorrect field ("%s") is provided in the view.`
                        ),
                        fieldName
                    );
                    this.notification.add({ title: warning, type: "danger" });
                }
                break;
            }
            default: {
                this.notification.add(this.env._t("Kanban: no action for type: ") + type, {
                    type: "danger",
                });
            }
        }
    }

    // ------------------------------------------------------------------------
    // Handlers
    // ------------------------------------------------------------------------

    onGroupClick(group, ev) {
        if (!ev.target.closest(".dropdown") && group.isFolded) {
            group.toggle();
        }
    }

    onRecordClick(record, ev) {
        if (ev.target.closest(GLOBAL_CLICK_CANCEL_SELECTORS.join(","))) {
            return;
        }
        this.props.openRecord(record);
    }

    onCardClicked(record, ev) {
        if (ev.target.closest(GLOBAL_CLICK_CANCEL_SELECTORS.join(","))) {
            return;
        }
        this.openRecord(record);
    }

    //-------------------------------------------------------------------------
    // KANBAN SPECIAL FUNCTIONS
    //
    // Note: some of these are snake_cased with not-so-self-explanatory names
    // for the sake of compatibility.
    // WOWL TODO: transpile the function calls in KanbanArchParser to better
    // names
    //-------------------------------------------------------------------------

    /**
     * Returns the image URL of a given field on a record.
     *
     * @param {Object} param0
     * @param {string} [param0.model] model name
     * @param {string} [param0.field] field name
     * @param {number | [number, ...any[]]} [param0.idOrIds] id or array
     *      starting with the id of the desired record.
     * @param {string} [param0.placeholder] fallback when the image does not
     *  exist
     * @param {Object} record the record corresponding to the current card
     * @returns {string}
     */
    imageSrcFromRecordInfo({ model, field, idOrIds, placeholder }, record) {
        const id = (Array.isArray(idOrIds) ? idOrIds[0] : idOrIds) || null;
        const isCurrentRecord =
            record.resModel === model && (record.resId === id || (!record.resId && !id));
        const fieldVal = record.data[field];
        if (isCurrentRecord && fieldVal && !isBinSize(fieldVal)) {
            // Use magic-word technique for detecting image type
            const type = fileTypeMagicWordMap[fieldVal[0]];
            return `data:image/${type};base64,${fieldVal}`;
        } else if (placeholder && (!model || !field || !id || !fieldVal)) {
            // Placeholder if either the model, field, id or value is missing or null.
            return placeholder;
        } else {
            // Else: fetches the image related to the given id.
            return url("/web/image", { model, field, id });
        }
    }

    /**
     * Returns the class name of a record according to its color.
     */
    kanban_color(value) {
        return `oe_kanban_color_${this.kanban_getcolor(value)}`;
    }

    /**
     * Returns the index of a color determined by a given record.
     */
    kanban_getcolor(value) {
        if (typeof value === "number") {
            return Math.round(value) % this.colors.length;
        } else if (typeof value === "string") {
            const charCodeSum = [...value].reduce((acc, _, i) => acc + value.charCodeAt(i), 0);
            return charCodeSum % this.colors.length;
        } else {
            return 0;
        }
    }

    /**
     * Returns the proper translated name of a record color.
     */
    kanban_getcolorname(value) {
        return this.colors[this.kanban_getcolor(value)];
    }

    /**
     * Checks if a html content is empty. If there are only formatting tags
     * with style attributes or a void content. Famous use case is
     * '<p style="..." class=".."><br></p>' added by some web editor(s).
     * Note that because the use of this method is limited, we ignore the cases
     * like there's one <img> tag in the content. In such case, even if it's the
     * actual content, we consider it empty.
     *
     * @param {string} innerHTML
     * @returns {boolean} true if no content found or if containing only formatting tags
     */
    isHtmlEmpty(innerHTML = "") {
        const div = Object.assign(document.createElement("div"), { innerHTML });
        return div.innerText.trim() === "";
    }
}

KanbanRenderer.template = "web.KanbanRenderer";
KanbanRenderer.components = {
    Field,
    KanbanColumnQuickCreate,
    KanbanRecordQuickCreate,
    ViewButton,
    KanbanAnimatedNumber,
    Dropdown,
    DropdownItem,
};
