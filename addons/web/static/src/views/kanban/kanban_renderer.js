/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Domain } from "@web/core/domain";
import { useAutofocus, useService, useListener } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { url } from "@web/core/utils/urls";
import { FieldColorPicker, fileTypeMagicWordMap } from "@web/fields/basic_fields";
import { Field } from "@web/fields/field";
import { useViewCompiler } from "@web/views/helpers/view_compiler";
import { isRelational } from "@web/views/helpers/view_utils";
import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { View } from "@web/views/view";
import { ViewButton } from "@web/views/view_button/view_button";

const { Component, hooks } = owl;
const { onWillUnmount, useExternalListener, useState, useSubEnv } = hooks;

const { RECORD_COLORS } = FieldColorPicker;

const GLOBAL_CLICK_CANCEL_SELECTORS = [".dropdown", ".oe_kanban_action"];
const isBinSize = (value) => /^\d+(\.\d*)? [^0-9]+$/.test(value);

const useSortable = (params) => {
    const {
        listSelector,
        itemSelector,
        containment,
        cursor,
        onItemEnter,
        onItemLeave,
        onListEnter,
        onListLeave,
        onStart,
        onStop,
        onDrop,
    } = params;
    const fullSelector = `${listSelector} ${itemSelector}`;

    let currentItem = null;
    let currentList = null;
    let ghost = null;

    let started = false;
    let locked = false;

    let offsetX = 0;
    let offsetY = 0;

    const cleanups = [];

    const addListener = (el, event, callback, options, timeout) => {
        el.addEventListener(event, callback, options);
        const cleanup = () => el.removeEventListener(event, callback, options);
        cleanups.push(() => (timeout ? setTimeout(cleanup) : cleanup()));
    };

    const addStyle = (el, style) => {
        const originalStyle = el.getAttribute("style");
        cleanups.push(() =>
            originalStyle ? el.setAttribute("style", originalStyle) : el.removeAttribute("style")
        );
        for (const key in style) {
            el.style[key] = style[key];
        }
    };

    const debounce = (callback) => {
        if (locked) {
            return;
        }
        locked = true;
        callback();
        requestAnimationFrame(() => (locked = false));
    };

    const cancelEvent = (ev) => {
        ev.stopPropagation();
        ev.stopImmediatePropagation();
        ev.preventDefault();
    };

    const onItemMouseenter = (ev) => {
        const item = ev.currentTarget;
        if (containment !== "parent" || item.closest(listSelector) === currentList) {
            console.log("ITEM ENTER");
            const pos = ghost.compareDocumentPosition(item);
            if (pos === 2 /* BEFORE */) {
                item.before(ghost);
            } else if (pos === 4 /* AFTER */) {
                item.after(ghost);
            }
        }
        if (onItemEnter) {
            onItemEnter(item);
        }
    };

    const onItemMouseleave = (ev) => {
        onItemLeave(ev.currentTarget);
    };

    const onListMouseenter = (ev) => {
        const list = ev.currentTarget;
        if (containment !== "parent") {
            console.log("LIST ENTER");
            list.appendChild(ghost);
        }
        if (onListEnter) {
            onListEnter(list);
        }
    };

    const onListMouseleave = (ev) => {
        onListLeave(ev.currentTarget);
    };

    const dragStart = () => {
        if (started) {
            return;
        }
        started = true;
        const { x, y, width, height } = currentItem.getBoundingClientRect();
        offsetX -= x;
        offsetY -= y;

        ghost = currentItem.cloneNode(true);
        ghost.style.opacity = 0;
        cleanups.push(() => ghost.remove());
        addListener(currentItem, "click", cancelEvent, true, true);

        for (const siblingList of document.querySelectorAll(listSelector)) {
            addListener(siblingList, "mouseenter", onListMouseenter);
            if (onListLeave) {
                addListener(siblingList, "mouseleave", onListMouseleave);
            }

            for (const siblingItem of siblingList.querySelectorAll(itemSelector)) {
                if (siblingItem !== currentItem && siblingItem !== ghost) {
                    addListener(siblingItem, "mouseenter", onItemMouseenter);
                    if (onItemLeave) {
                        addListener(siblingItem, "mouseleave", onItemMouseleave);
                    }
                }
            }
        }

        if (onStart) {
            onStart(currentList, currentItem);
        }

        currentItem.after(ghost);

        addStyle(currentItem, {
            position: "fixed",
            "pointer-events": "none",
            width: `${width}px`,
            height: `${height}px`,
        });

        if (cursor) {
            addStyle(document.body, { cursor });
        }
    };

    const drag = (x, y) => {
        debounce(() => {
            if (containment !== "parent") {
                currentItem.style.left = `${x - offsetX}px`;
            }
            currentItem.style.top = `${y - offsetY}px`;
        });
    };

    const dragStop = (cancelled = false) => {
        if (!started) {
            return;
        }
        if (onStop) {
            onStop(currentList, currentItem);
        }
        if (
            onDrop &&
            !cancelled &&
            ghost.previousElementSibling !== currentItem &&
            ghost.nextElementSibling !== currentItem
        ) {
            const previous = ghost.previousElementSibling;
            const parent = ghost.parentNode;
            onDrop({ previous, parent });
        }
        for (const cleanup of cleanups) {
            cleanup();
        }
        currentItem = null;
        ghost = null;
        started = false;
    };

    useListener("mousedown", fullSelector, (ev) => {
        currentItem = ev.target.closest(itemSelector);
        currentList = ev.target.closest(listSelector);
        offsetX = ev.clientX;
        offsetY = ev.clientY;
    });
    useExternalListener(window, "mousemove", (ev) => {
        if (!currentItem) {
            return;
        }
        dragStart();
        drag(ev.clientX, ev.clientY);
    });
    useExternalListener(window, "mouseup", () => dragStop(), true);
    useExternalListener(
        window,
        "keydown",
        (ev) => {
            switch (ev.key) {
                case "Escape":
                case "Tab": {
                    if (started) {
                        cancelEvent(ev);
                    }
                    dragStop(true);
                }
            }
        },
        true
    );
    onWillUnmount(() => dragStop(true));
};

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
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.colors = RECORD_COLORS;
        useSubEnv({ model: this.props.list.model });
        useAutofocus();
        if (this.props.info.recordsDraggable) {
            let dataRecordId;
            let dataListId;
            useSortable({
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
                    dataListId = Number(group.dataset.id);
                    dataRecordId = Number(item.dataset.id);
                    item.classList.add("o_currently_dragged", "ui-sortable-helper");
                },
                onStop(group, item) {
                    item.classList.remove("o_currently_dragged", "ui-sortable-helper");
                },
                onDrop: ({ previous, parent }) => {
                    const groupEl = parent.closest(".o_kanban_group");
                    const refId = previous ? Number(previous.dataset.id) : null;
                    const groupId = Number(groupEl.dataset.id);
                    this.env.model.moveRecord(dataRecordId, dataListId, refId, groupId);
                },
            });
        }
        useExternalListener(window, "keydown", this.onWindowKeydown);
        useExternalListener(window, "click", this.onWindowClick);
    }

    get context() {
        return this.props.context;
    }

    get progress() {
        return this.props.list.model.progress;
    }

    quickCreate(group) {
        const [groupByField] = this.props.list.model.root.groupBy;
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
            confirm: () => group.archive(),
            cancel: () => {},
        });
    }

    unarchiveGroup(group) {
        group.unarchive();
    }

    deleteGroup(group) {
        // TODO
        console.warn("TODO: Delete group", group.id);
    }

    openRecord(record) {
        const resIds = this.props.list.data.map((datapoint) => datapoint.resId);
        this.action.switchView("form", { resId: record.resId, resIds });
    }

    onGroupClick(group, ev) {
        if (!ev.target.closest(".dropdown") && !group.isLoaded) {
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
        const { data, isGrouped } = this.props.list;
        return isGrouped ? data.sort((a) => (a.value ? 1 : -1)) : data;
    }

    getGroupName({ count, displayName, isLoaded }) {
        return isLoaded ? displayName : `${displayName} (${count})`;
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

    getGroupClasses({ activeProgressValue, count, isLoaded, progress }) {
        const classes = [];
        if (!count) {
            classes.push("o_kanban_no_records");
        }
        if (!isLoaded) {
            classes.push("o_column_folded");
        }
        if (progress) {
            classes.push("o_kanban_has_progressbar");
            if (isLoaded && activeProgressValue) {
                const progressValue = progress.find((d) => d.value === activeProgressValue);
                classes.push("o_kanban_group_show", `o_kanban_group_show_${progressValue.color}`);
            }
        }
        return classes.join(" ");
    }

    getGroupUnloadedCount({ activeProgressValue, count, data, progress }) {
        if (activeProgressValue) {
            const progressValue = progress.find((d) => d.value === activeProgressValue);
            return progressValue.count - data.length;
        } else {
            return count - data.length;
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
                    for (const record of group.data) {
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
        group.loadMore();
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
        const record = this.props.list.model.get({ resId: id }) || { data: {} };
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
