/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Domain } from "@web/core/domain";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { url } from "@web/core/utils/urls";
import { FieldColorPicker, fileTypeMagicWordMap } from "@web/fields/basic_fields";
import { Field } from "@web/fields/field";
import { useViewCompiler } from "@web/views/helpers/view_compiler";
import { isRelational } from "@web/views/helpers/view_utils";
import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { useSortable } from "@web/views/kanban/kanban_sortable";
import { View } from "@web/views/view";
import { ViewButton } from "@web/views/view_button/view_button";

const { Component, hooks } = owl;
const { useExternalListener, useState } = hooks;

const { RECORD_COLORS } = FieldColorPicker;

const GLOBAL_CLICK_CANCEL_SELECTORS = [".dropdown", ".oe_kanban_action"];
const isBinSize = (value) => /^\d+(\.\d*)? [^0-9]+$/.test(value);

export class KanbanRenderer extends Component {
    setup() {
        const { arch, cards, className, fields, xmlDoc } = this.props.info;
        this.cards = cards;
        this.className = className;
        this.cardTemplate = useViewCompiler(KanbanCompiler, arch, fields, xmlDoc);
        this.state = useState({
            quickCreate: [],
        });
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.colors = RECORD_COLORS;
        useAutofocus();
        useExternalListener(window, "keydown", this.onWindowKeydown);
        useExternalListener(window, "click", this.onWindowClick);
        // Sortable
        let dataRecordId;
        let dataListId;
        useSortable({
            activate: () => this.recordsDraggable,
            listSelector: ".o_kanban_group",
            itemSelector: ".o_kanban_record:not(.o_updating)",
            // TODO recordsMovable = whether the records can be moved accross columns
            // containment: this.props.info.recordsMovable ? false : "parent",
            cursor: "move",
            onListEnter(group) {
                group.classList.add("o_kanban_hover");
            },
            onListLeave(group) {
                group.classList.remove("o_kanban_hover");
            },
            onStart(group, item) {
                dataListId = group.dataset.id;
                dataRecordId = item.dataset.id;
                item.classList.add("o_currently_dragged", "ui-sortable-helper");
            },
            onStop(group, item) {
                item.classList.remove("o_currently_dragged", "ui-sortable-helper");
            },
            onDrop: async ({ previous, parent }) => {
                const groupEl = parent.closest(".o_kanban_group");
                const refId = previous ? previous.dataset.id : null;
                const groupId = groupEl.dataset.id;
                const group = this.props.list.groups.find((g) => g.id === groupId);
                await this.props.list.moveRecord(dataRecordId, dataListId, refId, groupId);
                if (group.isFolded) {
                    await group.toggle();
                }
            },
        });
        useSortable({
            activate: () => this.columnsDraggable,
            axis: "x",
            itemSelector: ".o_kanban_group",
            handle: ".o_column_title",
            cursor: "move",
            onStart(group, item) {
                dataListId = Number(item.dataset.id);
            },
            onDrop: ({ previous }) => {
                const refId = Number(previous.dataset.id);
                this.props.list.resequence(dataListId, refId);
            },
        });
    }

    get context() {
        return this.props.context;
    }

    get progress() {
        return this.props.list.model.progress;
    }

    get recordsDraggable() {
        return this.props.list.isGrouped && this.props.info.recordsDraggable;
    }

    get columnsDraggable() {
        return this.props.list.isGrouped && this.props.list.groupByField.type === "many2one";
    }

    quickCreate(group) {
        const [groupByField] = this.props.list.groupBy;
        this.state.quickCreate[group.id] = {
            [groupByField]: Array.isArray(group.value) ? group.value[0] : group.value,
        };
    }

    toggleGroup(group) {
        group.toggle();
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
        // TODO
        console.warn("TODO: Delete group", group.id);
    }

    openRecord(record) {
        this.props.openRecord(record);
    }

    onGroupClick(group, ev) {
        if (!ev.target.closest(".dropdown") && group.isFolded) {
            group.toggle();
        }
    }

    selectColor(record, colorIndex) {
        // TODO
        console.warn("TODO: Update record", record.id, {
            [this.props.info.colorField]: colorIndex,
        });
    }

    triggerAction(record, params) {
        const { type } = params;
        switch (type) {
            case "edit":
            case "open": {
                this.openRecord(record);
                break;
            }
            case "delete": {
                // TODO
                console.warn("TODO: Delete record", record.id);
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

    /**
     * When the kanban records are grouped, the 'false' or 'undefined' column
     * must appear first.
     * @returns {any[]}
     */
    getGroupsOrRecords() {
        const { list } = this.props;
        if (list.isGrouped) {
            return list.groups
                .sort((a) => (a.value ? 0 : -1))
                .map((group) => ({ group, key: group.value }));
        } else {
            return list.records.map((record) => ({ record, key: record.resId }));
        }
    }

    getGroupName({ count, displayName, isFolded }) {
        return isFolded ? `${displayName} (${count})` : displayName;
    }

    canArchiveGroup(group) {
        const { activeActions } = this.props.info;
        const { groupByField } = this.props.list;
        const hasActiveField = "active" in group.fields;
        return activeActions.groupArchive && hasActiveField && groupByField.type !== "many2many";
    }

    canCreateGroup() {
        const { activeActions } = this.props.info;
        const { groupByField } = this.props.list;
        return activeActions.groupCreate && groupByField.type === "many2one";
    }

    canDeleteGroup(group) {
        const { activeActions } = this.props.info;
        const { groupByField } = this.props.list;
        return activeActions.groupDelete && isRelational(groupByField) && group.value;
    }

    canEditGroup(group) {
        const { activeActions } = this.props.info;
        const { groupByField } = this.props.list;
        return activeActions.groupEdit && isRelational(groupByField) && group.value;
    }

    getGroupClasses({ activeProgressValue, count, isFolded, progress }) {
        const classes = [];
        if (!count) {
            classes.push("o_kanban_no_records");
        }
        if (isFolded) {
            classes.push("o_column_folded");
        }
        if (progress) {
            classes.push("o_kanban_has_progressbar");
            if (!isFolded && activeProgressValue) {
                const progressValue = progress.find((d) => d.value === activeProgressValue);
                classes.push("o_kanban_group_show", `o_kanban_group_show_${progressValue.color}`);
            }
        }
        return classes.join(" ");
    }

    getGroupUnloadedCount({ activeProgressValue, count, list, progress }) {
        if (activeProgressValue) {
            const progressValue = progress.find((d) => d.value === activeProgressValue);
            return progressValue.count - list.records.length;
        } else {
            return count - list.records.length;
        }
    }

    getRecordProgressColor({ activeProgressValue }) {
        if (!activeProgressValue) {
            return "";
        }
        const colorClass = this.progress.colors[activeProgressValue];
        return `oe_kanban_card_${colorClass || "muted"}`;
    }

    getProgressSumField(group) {
        let string = "";
        let value = 0;
        const { sumField } = this.progress;
        if (sumField) {
            const field = group.fields[sumField];
            if (field) {
                string = field.string;
                if (group.activeProgressValue) {
                    value = 0;
                    for (const record of group.list.records) {
                        value += record.data[sumField];
                    }
                } else {
                    value = group.aggregates[sumField];
                }
            }
        } else {
            string = this.env._t("Count");
            value = group.count;
        }
        return { string, value };
    }

    getColumnTitle(group) {
        return Array.isArray(group.value) ? group.value[1] : group.value;
    }

    loadMore(group) {
        group.list.loadMore();
    }

    onCardClicked(record, ev) {
        if (ev.target.closest(GLOBAL_CLICK_CANCEL_SELECTORS.join(","))) {
            return;
        }
        this.openRecord(record);
    }

    onWindowKeydown(ev) {
        if (this.state.quickCreateGroup && ev.key === "Escape") {
            this.state.quickCreateGroup = false;
        }
    }

    onWindowClick(ev) {
        if (this.state.quickCreateGroup && !ev.target.closest(".o_column_quick_create")) {
            this.state.quickCreateGroup = false;
        }
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
     * Computes a given domain.
     */
    kanban_compute_domain(domain) {
        return new Domain(domain).compute(this.props.domain);
    }
}

KanbanRenderer.template = "web.KanbanRenderer";
KanbanRenderer.components = { Field, View, ViewButton };
