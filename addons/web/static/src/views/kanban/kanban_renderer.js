/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { url } from "@web/core/utils/urls";
import { ColorPickerField } from "@web/fields/color_picker_field";
import { Field } from "@web/fields/field";
import { fileTypeMagicWordMap } from "@web/fields/image_field";
import { session } from "@web/session";
import { FormRenderer } from "@web/views/form/form_renderer";
import { useViewCompiler } from "@web/views/helpers/view_compiler";
import { isRelational } from "@web/views/helpers/view_utils";
import { KanbanAnimatedNumber } from "@web/views/kanban/kanban_animated_number";
import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { useSortable } from "@web/views/kanban/kanban_sortable";
import { isAllowedDateField } from "@web/views/relational_model";
import { ViewButton } from "@web/views/view_button/view_button";
import { useBounceButton } from "@web/views/helpers/view_hook";

const { Component, useExternalListener, useState, useRef } = owl;
const { RECORD_COLORS } = ColorPickerField;

const DRAGGABLE_GROUP_TYPES = ["many2one"];
const MOVABLE_RECORD_TYPES = ["char", "boolean", "integer", "selection", "many2one"];
const GLOBAL_CLICK_CANCEL_SELECTORS = ["a", ".dropdown", ".oe_kanban_action"];
const isBinSize = (value) => /^\d+(\.\d*)? [^0-9]+$/.test(value);

export class KanbanRenderer extends Component {
    setup() {
        const { arch, cards, className, fields, xmlDoc, examples } = this.props.info;
        this.cards = cards;
        this.className = className;
        this.cardTemplate = useViewCompiler(KanbanCompiler, arch, fields, xmlDoc);
        this.state = useState({
            quickCreateDisabled: false,
            quickCreateGroup: this.props.list.isGrouped && this.props.list.groups.length === 0,
            newGroup: "",
        });
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.mousedownTarget = null;
        this.colors = RECORD_COLORS;
        this.exampleData = registry.category("kanban_examples").get(examples, null);
        this.ghostColumns = this.generateGhostColumns();
        useAutofocus();
        useExternalListener(window, "click", this.onWindowClick, true);
        useExternalListener(window, "keydown", this.onWindowKeydown);
        useExternalListener(window, "mousedown", this.onWindowMousedown);
        // Sortable
        let dataRecordId;
        let dataGroupId;
        const rootRef = useRef("root");
        useSortable({
            ref: rootRef,
            setup: () =>
                this.canResequenceRecords && {
                    listSelector: ".o_kanban_group",
                    itemSelector: ".o_record_draggable",
                    containment: this.canMoveRecords ? false : "parent",
                    axis: this.canMoveRecords ? false : "y",
                    cursor: "move",
                },
            onListEnter(group) {
                group.classList.add("o_kanban_hover");
            },
            onListLeave(group) {
                group.classList.remove("o_kanban_hover");
            },
            onStart(group, item) {
                dataGroupId = group.dataset.id;
                dataRecordId = item.dataset.id;
                item.classList.add("o_dragged");
            },
            onStop(group, item) {
                item.classList.remove("o_dragged");
            },
            onDrop: async ({ item, previous, parent }) => {
                item.classList.remove("o_record_draggable");
                const groupEl = parent.closest(".o_kanban_group");
                const refId = previous ? previous.dataset.id : null;
                const groupId = groupEl.dataset.id;
                await this.props.list.moveRecord(dataRecordId, dataGroupId, refId, groupId);
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
        return this.props.list.isGrouped && this.props.info.recordsDraggable;
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
            if (this.state.quickCreateGroup) {
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
                .map((group) => ({ group, key: group.value }));
        } else {
            return list.records.map((record) => ({ record, key: record.resId }));
        }
    }

    getGroupName({ count, displayName, isFolded }) {
        return isFolded ? `${displayName} (${count})` : displayName;
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
        return total - group.list.count;
    }

    getRecordClasses(record, group) {
        const classes = ["o_kanban_record"];
        const { fieldName } = this.props.list.model.progressAttributes || {};
        if (group && record.data[fieldName]) {
            const value = record.data[fieldName];
            const { color } = group.progressValues.find((p) => p.value === value);
            classes.push(`oe_kanban_card_${color}`);
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
        let value = group.count;
        let currency = false;
        let title = this.env._t("Count");
        const { sumField } = this.props.list.model.progressAttributes;
        if (sumField) {
            const { currency_field, name } = sumField;
            title = sumField.string;
            if (group.activeProgressValue !== null) {
                value = group.list.records.reduce((acc, r) => acc + r.data[name], 0);
            } else {
                value = group.aggregates[name];
            }
            if (value && currency_field) {
                currency = session.currencies[session.company_currency_id];
            }
        }
        return { value: value || 0, currency, title };
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
        const { activeActions } = this.props.info;
        const hasActiveField = "active" in group.fields;
        return activeActions.groupArchive && hasActiveField && !this.props.list.groupedBy("m2m");
    }

    canCreateGroup() {
        const { activeActions } = this.props.info;
        return activeActions.groupCreate && this.props.list.groupedBy("m2o");
    }

    canDeleteGroup(group) {
        const { activeActions } = this.props.info;
        const { groupByField } = this.props.list;
        return activeActions.groupDelete && isRelational(groupByField) && group.value;
    }

    canDeleteRecord() {
        const { activeActions } = this.props.info;
        return activeActions.delete && !this.props.list.groupedBy("m2m");
    }

    canEditGroup(group) {
        const { activeActions } = this.props.info;
        const { groupByField } = this.props.list;
        return activeActions.groupEdit && isRelational(groupByField) && group.value;
    }

    canEditRecord() {
        return this.props.info.activeActions.edit;
    }

    // ------------------------------------------------------------------------
    // Edition methods
    // ------------------------------------------------------------------------

    async createGroup() {
        if (this.state.newGroup.length) {
            await this.props.list.createGroup(this.state.newGroup);
        }
        this.state.newGroup = "";
    }

    cancelQuickCreate(force = false) {
        for (const group of this.props.list.groups) {
            group.list.cancelQuickCreate(force);
        }
    }

    async validateQuickCreate(group, editAfterCreate) {
        if (this.state.quickCreateDisabled) {
            return;
        }
        this.state.quickCreateDisabled = true;
        const record = await group.validateQuickCreate();
        this.state.quickCreateDisabled = false;
        if (editAfterCreate) {
            await this.props.openRecord(record);
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
                    this.state.quickCreateGroup = true;
                }
            },
            cancel: () => {},
        });
    }

    deleteRecord(record, group) {
        const { list } = group || this.props;
        this.dialog.add(ConfirmationDialog, {
            body: this.env._t("Are you sure you want to delete this record?"),
            confirm: () => list.deleteRecords([record]),
            cancel: () => {},
        });
    }

    selectColor(record, colorIndex) {
        // TODO
        console.warn("TODO: Update record", record.id, {
            [this.props.info.colorField]: colorIndex,
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

    showExamples() {
        this.dialog.add(KanbanExamplesDialog, {
            examples: this.exampleData.examples,
            applyExamplesText:
                this.exampleData.applyExamplesText || this.env._t("Use This For My Kanban"),
            applyExamples: (index) => {
                for (const groupName of this.exampleData.examples[index].columns) {
                    this.props.list.createGroup(groupName);
                }
            },
        });
    }

    // ------------------------------------------------------------------------
    // Handlers
    // ------------------------------------------------------------------------

    onAddGroupKeydown(ev) {
        if (ev.key === "Enter") {
            this.createGroup();
        }
    }

    onGroupClick(group, ev) {
        if (!ev.target.closest(".dropdown") && group.isFolded) {
            group.toggle();
        }
    }

    onQuickCreateKeydown(group, ev) {
        if (ev.key === "Enter") {
            this.validateQuickCreate(group, false);
        }
    }

    onRecordClick(record, ev) {
        if (ev.target.closest(GLOBAL_CLICK_CANCEL_SELECTORS.join(","))) {
            return;
        }
        this.props.openRecord(record);
    }

    onWindowClick(ev) {
        if (!this.props.list.isGrouped) {
            return;
        }
        const target = this.mousedownTarget || ev.target;
        if (!target.closest(".o_kanban_quick_create")) {
            this.cancelQuickCreate();
        }
        if (!target.closest(".o_column_quick_create") && this.props.list.groups.length > 0) {
            this.state.quickCreateGroup = false;
        }
        this.mousedownTarget = null;
    }

    onWindowKeydown(ev) {
        if (!this.props.list.isGrouped) {
            return;
        }
        if (ev.key === "Escape" && this.props.list.groups.length > 0) {
            this.state.quickCreateGroup = false;
            this.cancelQuickCreate(true);
        }
    }

    onWindowMousedown(ev) {
        this.mousedownTarget = ev.target;
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
    // Note: these are snake_cased with not-so-self-explanatory names for the
    // sake of compatibility.
    //-------------------------------------------------------------------------

    /**
     * Returns the image URL of a given record.
     * @param {string} model model name
     * @param {string} field field name
     * @param {number | number[]} idOrIds
     * @param {string} placeholder
     * @returns {string}
     */
    kanban_image(model, field, idOrIds, placeholder) {
        const id = (Array.isArray(idOrIds) ? idOrIds[0] : idOrIds) || null;
        const record = /** this.props.list.model.get({ resId: id }) || */ { data: {} };
        const value = record.data[field];
        if (value && !isBinSize(value)) {
            // Use magic-word technique for detecting image type
            const type = fileTypeMagicWordMap[value[0]];
            return `data:image/${type};base64,${value}`;
        } else if (placeholder && (!model || !field || !id || !value)) {
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
    FormRenderer,
    ViewButton,
    KanbanAnimatedNumber,
    Dropdown,
    DropdownItem,
};

class KanbanExamplesDialog extends Dialog {
    setup() {
        super.setup(...arguments);
        this.navList = useRef("navList");
    }

    random(min, max) {
        return new Array(Math.floor(Math.random() * (max - min) + min));
    }

    applyExamples() {
        const ul = this.navList.el;
        // FIXME WOWL: make an owl nav/tabs component so we don't have to do this
        const activeNavItem = ul.querySelector(".nav-link.active").parentElement;
        const index = [...ul.children].indexOf(activeNavItem);
        this.props.applyExamples(index);
        this.close();
    }
}
KanbanExamplesDialog.bodyTemplate = "web.KanbanExamplesDialog";
KanbanExamplesDialog.footerTemplate = "web.KanbanExamplesDialogFooter";
KanbanExamplesDialog.title = _lt("Kanban Examples");
KanbanExamplesDialog.contentClass = "o_kanban_examples_dialog";
