/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { useSortable } from "@web/core/utils/sortable";
import { sprintf } from "@web/core/utils/strings";
import { isNull } from "@web/views/utils";
import { ColumnProgress } from "@web/views/view_components/column_progress";
import { useBounceButton } from "@web/views/view_hook";
import { KanbanColumnQuickCreate } from "./kanban_column_quick_create";
import { KanbanHeader } from "./kanban_header";
import { KanbanRecord } from "./kanban_record";
import { KanbanRecordQuickCreate } from "./kanban_record_quick_create";

import { Component, onPatched, onWillDestroy, onWillPatch, useRef, useState } from "@odoo/owl";

const DRAGGABLE_GROUP_TYPES = ["many2one"];
const MOVABLE_RECORD_TYPES = ["char", "boolean", "integer", "selection", "many2one"];

function validateColumnQuickCreateExamples(data) {
    const { allowedGroupBys = [], examples = [], foldField = "" } = data;
    if (!allowedGroupBys.length) {
        throw new Error("The example data must contain an array of allowed groupbys");
    }
    if (!examples.length) {
        throw new Error("The example data must contain an array of examples");
    }
    const someHasFoldedColumns = examples.some(({ foldedColumns = [] }) => foldedColumns.length);
    if (!foldField && someHasFoldedColumns) {
        throw new Error("The example data must contain a fold field if there are folded columns");
    }
}

export class KanbanRenderer extends Component {
    static template = "web.KanbanRenderer";
    static components = {
        Dropdown,
        DropdownItem,
        ColumnProgress,
        KanbanColumnQuickCreate,
        KanbanHeader,
        KanbanRecord,
        KanbanRecordQuickCreate,
    };
    static props = [
        "archInfo",
        "Compiler?", // optional in stable for backward compatibility
        "list",
        "openRecord",
        "readonly",
        "forceGlobalClick?",
        "noContentHelp?",
        "scrollTop?",
        "canQuickCreate?",
        "quickCreateState?",
    ];

    static defaultProps = {
        scrollTop: () => {},
        quickCreateState: { groupId: false },
        tooltipInfo: {},
    };

    setup() {
        this.dialogClose = [];
        /**
         * @type {{ processedIds: string[], columnQuickCreateIsFolded: boolean }}
         */
        this.state = useState({
            processedIds: [],
            columnQuickCreateIsFolded:
                !this.props.list.isGrouped || this.props.list.groups.length > 0,
        });
        this.dialog = useService("dialog");
        this.exampleData = registry
            .category("kanban_examples")
            .get(this.props.archInfo.examples, null);
        if (this.exampleData) {
            validateColumnQuickCreateExamples(this.exampleData);
        }
        this.ghostColumns = this.generateGhostColumns();

        // Sortable
        let dataRecordId;
        let dataGroupId;
        this.rootRef = useRef("root");
        if (this.canUseSortable) {
            useSortable({
                enable: () => this.canResequenceRecords,
                // Params
                ref: this.rootRef,
                elements: ".o_draggable",
                ignore: ".dropdown",
                groups: () => this.props.list.isGrouped && ".o_kanban_group",
                connectGroups: () => this.canMoveRecords,
                cursor: "move",
                // Hooks
                onDragStart: (params) => {
                    const { element, group } = params;
                    dataRecordId = element.dataset.id;
                    dataGroupId = group && group.dataset.id;
                    return this.sortStart(params);
                },
                onDragEnd: (params) => this.sortStop(params),
                onGroupEnter: (params) => this.sortRecordGroupEnter(params),
                onGroupLeave: (params) => this.sortRecordGroupLeave(params),
                onDrop: (params) => this.sortRecordDrop(dataRecordId, dataGroupId, params),
            });
            useSortable({
                enable: () => this.canResequenceGroups,
                // Params
                ref: this.rootRef,
                elements: ".o_group_draggable",
                handle: ".o_column_title",
                cursor: "move",
                // Hooks
                onDragStart: (params) => {
                    const { element } = params;
                    dataGroupId = element.dataset.id;
                    return this.sortStart(params);
                },
                onDragEnd: (params) => this.sortStop(params),
                onDrop: (params) => this.sortGroupDrop(dataGroupId, params),
            });
        }

        useBounceButton(this.rootRef, (clickedEl) => {
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
        onWillDestroy(() => {
            this.dialogClose.forEach((close) => close());
        });

        if (this.env.searchModel) {
            useBus(this.env.searchModel, "focus-view", () => {
                const { model } = this.props.list;
                if (model.useSampleModel || !model.hasData()) {
                    return;
                }
                const firstCard = this.rootRef.el.querySelector(".o_kanban_record");
                if (firstCard) {
                    // Focus first kanban card
                    firstCard.focus();
                }
            });
        }

        useHotkey(
            "Enter",
            ({ target }) => {
                if (!target.classList.contains("o_kanban_record")) {
                    return;
                }

                // Open first link
                const firstLink = target.querySelector(".oe_kanban_global_click, a, button");
                if (firstLink && firstLink instanceof HTMLElement) {
                    firstLink.click();
                }
                return;
            },
            { area: () => this.rootRef.el }
        );

        const arrowsOptions = { area: () => this.rootRef.el, allowRepeat: true };
        if (this.env.searchModel) {
            useHotkey(
                "ArrowUp",
                ({ area }) => {
                    if (!this.focusNextCard(area, "up")) {
                        this.env.searchModel.trigger("focus-search");
                    }
                },
                arrowsOptions
            );
        }
        useHotkey("ArrowDown", ({ area }) => this.focusNextCard(area, "down"), arrowsOptions);
        useHotkey("ArrowLeft", ({ area }) => this.focusNextCard(area, "left"), arrowsOptions);
        useHotkey("ArrowRight", ({ area }) => this.focusNextCard(area, "right"), arrowsOptions);

        let previousScrollTop = 0;
        onWillPatch(() => {
            previousScrollTop = this.rootRef.el.scrollTop;
        });
        onPatched(() => {
            this.rootRef.el.scrollTop = previousScrollTop;
        });
    }

    // ------------------------------------------------------------------------
    // Getters
    // ------------------------------------------------------------------------

    get canUseSortable() {
        return !this.env.isSmall;
    }

    get canMoveRecords() {
        if (!this.canResequenceRecords) {
            return false;
        }
        const { fields, groupByField } = this.props.list;
        if (!groupByField) {
            return true;
        }
        const { name, modifiers } = groupByField;
        const isReadonly =
            modifiers && "readonly" in modifiers
                ? modifiers.readonly === true
                : fields[name].readonly;
        return !isReadonly && this.isMovableField(groupByField);
    }

    get canResequenceGroups() {
        if (!this.props.list.isGrouped) {
            return false;
        }
        const { type } = this.props.list.groupByField;
        const { groupsDraggable } = this.props.archInfo;
        return groupsDraggable && DRAGGABLE_GROUP_TYPES.includes(type);
    }

    get canResequenceRecords() {
        const { isGrouped, orderBy } = this.props.list;
        const { handleField, recordsDraggable } = this.props.archInfo;
        return Boolean(
            recordsDraggable &&
                (isGrouped || (handleField && (!orderBy[0] || orderBy[0].name === handleField)))
        );
    }

    get showNoContentHelper() {
        const { model, isGrouped, groupByField, groups } = this.props.list;
        if (model.useSampleModel) {
            return true;
        }
        if (isGrouped) {
            if (this.props.quickCreateState.groupId) {
                return false;
            }
            if (this.canCreateGroup() && !this.state.columnQuickCreateIsFolded) {
                return false;
            }
            if (groups.length === 0) {
                return groupByField.type !== "many2one";
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
                    key: isNull(group.value) ? `group_key_${i}` : String(group.value),
                }));
        } else {
            return list.records.map((record) => ({ record, key: record.id }));
        }
    }

    /**
     * @param {RelationalGroup} group
     * @param {boolean} isGroupProcessing
     * @returns {string}
     */
    getGroupClasses(group, isGroupProcessing) {
        const classes = [];
        if (!isGroupProcessing && this.canResequenceGroups && group.value) {
            classes.push("o_group_draggable");
        }
        if (!group.count) {
            classes.push("o_kanban_no_records");
        }
        if (!this.env.isSmall && group.isFolded) {
            classes.push("o_column_folded");
        }
        if (!group.isFolded) {
            classes.push("bg-100");
        }
        if (group.progressBars.length) {
            classes.push("o_kanban_has_progressbar");
            if (!group.isFolded && group.hasActiveProgressValue) {
                const progressBar = group.activeProgressBar;
                classes.push("o_kanban_group_show", `o_kanban_group_show_${progressBar.color}`);
            }
        }
        return classes.join(" ");
    }

    getGroupUnloadedCount(group) {
        const progressBar = group.activeProgressBar;
        const records = group.list.records.filter((r) => !r.isInQuickCreation);
        return (progressBar ? progressBar.count : group.count) - records.length;
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

    /**
     * @param {string} id
     * @returns {boolean}
     */
    isProcessing(id) {
        return this.state.processedIds.includes(id);
    }

    isMovableField(field) {
        return MOVABLE_RECORD_TYPES.includes(field.type);
    }

    // ------------------------------------------------------------------------
    // Permissions
    // ------------------------------------------------------------------------

    canCreateGroup() {
        const { activeActions } = this.props.archInfo;
        return activeActions.createGroup && this.props.list.groupByField.type === "many2one";
    }

    canQuickCreate() {
        return this.props.canQuickCreate;
    }

    // ------------------------------------------------------------------------
    // Edition methods
    // ------------------------------------------------------------------------

    async validateQuickCreate(recordId, mode, group) {
        this.props.quickCreateState.groupId = false;
        if (mode === "add") {
            this.props.quickCreateState.groupId = group.id;
        }
        const record = await group.addExistingRecord(recordId, true);
        group.model.bus.trigger("group-updated", {
            group: group,
            withProgressBars: true,
        });
        if (mode === "edit") {
            await this.props.openRecord(record, "edit");
        }
    }

    cancelQuickCreate() {
        this.props.quickCreateState.groupId = false;
    }

    async deleteGroup(group) {
        await this.props.list.deleteGroups([group]);
        if (this.props.list.groups.length === 0) {
            this.state.columnQuickCreateIsFolded = false;
        }
    }

    toggleGroup(group) {
        return group.toggle();
    }

    loadMore(group) {
        return group.list.loadMore();
    }

    /**
     * @param {string} id
     * @param {boolean} isProcessing
     */
    toggleProcessing(id, isProcessing) {
        if (isProcessing) {
            this.state.processedIds = [...this.state.processedIds, id];
        } else {
            this.state.processedIds = this.state.processedIds.filter(
                (processedId) => processedId !== id
            );
        }
    }

    // ------------------------------------------------------------------------
    // Handlers
    // ------------------------------------------------------------------------

    async onGroupClick(group, ev) {
        if (!this.env.isSmall && group.isFolded) {
            await group.toggle();
            this.props.scrollTop();
        }
    }

    /**
     * @param {string} dataGroupId
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} [params.group]
     * @param {HTMLElement} [params.next]
     * @param {HTMLElement} [params.parent]
     * @param {HTMLElement} [params.previous]
     */
    async sortGroupDrop(dataGroupId, { previous }) {
        this.toggleProcessing(dataGroupId, true);

        const refId = previous ? previous.dataset.id : null;
        await this.props.list.resequence(dataGroupId, refId);

        this.toggleProcessing(dataGroupId, false);
    }

    /**
     * @param {string} dataRecordId
     * @param {string} dataGroupId
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} [params.group]
     * @param {HTMLElement} [params.next]
     * @param {HTMLElement} [params.parent]
     * @param {HTMLElement} [params.previous]
     */
    async sortRecordDrop(dataRecordId, dataGroupId, { element, parent, previous }) {
        if (
            !this.props.list.isGrouped ||
            parent.classList.contains("o_kanban_hover") ||
            parent.dataset.id === element.parentElement.dataset.id
        ) {
            this.toggleProcessing(dataRecordId, true);

            parent?.classList.remove("o_kanban_hover");
            while (previous && !previous.dataset.id) {
                previous = previous.previousElementSibling;
            }
            const refId = previous ? previous.dataset.id : null;
            const targetGroupId = parent?.dataset.id;
            await this.props.list.moveRecord(dataRecordId, dataGroupId, refId, targetGroupId);

            this.toggleProcessing(dataRecordId, false);
        }
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.group
     */
    sortRecordGroupEnter({ group }) {
        group.classList.add("o_kanban_hover");
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.group
     */
    sortRecordGroupLeave({ group }) {
        group.classList.remove("o_kanban_hover");
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} [params.group]
     */
    sortStart({ element }) {
        element.classList.add("shadow");
    }

    /**
     * @param {Object} params
     * @param {HTMLElement} params.element
     * @param {HTMLElement} [params.group]
     */
    sortStop({ element, group }) {
        element.classList.remove("shadow");
        if (group) {
            group.classList.remove("o_kanban_hover");
        }
    }

    /**
     * Focus next card in the area within the chosen direction.
     *
     * @param {HTMLElement} area
     * @param {"down"|"up"|"right"|"left"} direction
     * @returns {true?} true if the next card has been focused
     */
    focusNextCard(area, direction) {
        const { isGrouped } = this.props.list;
        const closestCard = document.activeElement.closest(".o_kanban_record");
        if (!closestCard) {
            return;
        }
        const groups = isGrouped ? [...area.querySelectorAll(".o_kanban_group")] : [area];
        const cards = [...groups]
            .map((group) => [...group.querySelectorAll(".o_kanban_record")])
            .filter((group) => group.length);

        let iGroup;
        let iCard;
        for (iGroup = 0; iGroup < cards.length; iGroup++) {
            const i = cards[iGroup].indexOf(closestCard);
            if (i !== -1) {
                iCard = i;
                break;
            }
        }
        // Find next card to focus
        let nextCard;
        switch (direction) {
            case "down":
                nextCard = iCard < cards[iGroup].length - 1 && cards[iGroup][iCard + 1];
                break;
            case "up":
                nextCard = iCard > 0 && cards[iGroup][iCard - 1];
                break;
            case "right":
                if (isGrouped) {
                    nextCard = iGroup < cards.length - 1 && cards[iGroup + 1][0];
                } else {
                    nextCard = iCard < cards[0].length - 1 && cards[0][iCard + 1];
                }
                break;
            case "left":
                if (isGrouped) {
                    nextCard = iGroup > 0 && cards[iGroup - 1][0];
                } else {
                    nextCard = iCard > 0 && cards[0][iCard - 1];
                }
                break;
        }

        if (nextCard && nextCard instanceof HTMLElement) {
            nextCard.focus();
            return true;
        }
    }
}
