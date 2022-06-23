/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { RPCError } from "@web/core/network/rpc_service";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { useSortable } from "@web/core/utils/sortable";
import { sprintf } from "@web/core/utils/strings";
import { session } from "@web/session";
import { isAllowedDateField } from "@web/views/relational_model";
import { isRelational } from "@web/views/utils";
import { FormViewDialog } from "web.view_dialogs";
import { standaloneAdapter } from "web.OwlCompatibility";
import { useBounceButton } from "@web/views/view_hook";
import { KanbanAnimatedNumber } from "./kanban_animated_number";
import { KanbanColumnQuickCreate } from "./kanban_column_quick_create";
import { KanbanRecord } from "./kanban_record";
import { KanbanRecordQuickCreate } from "./kanban_record_quick_create";

const { Component, useState, useRef, onWillDestroy } = owl;

function isNull(value) {
    return [null, undefined].includes(value);
}

const DRAGGABLE_GROUP_TYPES = ["many2one"];
const MOVABLE_RECORD_TYPES = ["char", "boolean", "integer", "selection", "many2one"];

export class KanbanRenderer extends Component {
    setup() {
        this.dialogClose = [];
        this.state = useState({
            columnQuickCreateIsFolded:
                !this.props.list.isGrouped || this.props.list.groups.length > 0,
        });
        this.dialog = useService("dialog");
        this.exampleData = registry
            .category("kanban_examples")
            .get(this.props.archInfo.examples, null);
        this.ghostColumns = this.generateGhostColumns();

        // Sortable
        let dataRecordId;
        let dataGroupId;
        const rootRef = useRef("root");
        if (!this.env.isSmall) {
            useSortable({
                enable: () => this.canResequenceRecords,
                // Params
                ref: rootRef,
                elements: ".o_record_draggable",
                groups: () => this.props.list.isGrouped && ".o_kanban_group",
                connectGroups: () => this.canMoveRecords,
                cursor: "move",
                // Hooks
                onStart: (group, element) => {
                    dataRecordId = element.dataset.id;
                    if (group) {
                        dataGroupId = group.dataset.id;
                    }
                    element.classList.add("o_dragged");
                },
                onGroupEnter: (group) => group.classList.add("o_kanban_hover"),
                onGroupLeave: (group) => group.classList.remove("o_kanban_hover"),
                onStop: (_group, element) => element.classList.remove("o_dragged"),
                onDrop: async ({ element, previous, parent }) => {
                    element.classList.remove("o_record_draggable");
                    const refId = previous ? previous.dataset.id : null;
                    const targetGroupId = parent && parent.dataset.id;
                    await this.props.list.moveRecord(
                        dataRecordId,
                        dataGroupId,
                        refId,
                        targetGroupId
                    );
                    element.classList.add("o_record_draggable");
                },
            });
            useSortable({
                enable: () => this.canResequenceGroups,
                // Params
                ref: rootRef,
                elements: ".o_group_draggable",
                handle: ".o_column_title",
                cursor: "move",
                // Hooks
                onStart: (_group, element) => {
                    dataGroupId = element.dataset.id;
                    element.classList.add("o_dragged");
                },
                onStop: (_group, element) => element.classList.remove("o_dragged"),
                onDrop: async ({ element, previous }) => {
                    element.classList.remove("o_group_draggable");
                    const refId = previous ? previous.dataset.id : null;
                    await this.props.list.resequence(dataGroupId, refId);
                    element.classList.add("o_group_draggable");
                },
            });
        }

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
        onWillDestroy(() => {
            this.dialogClose.forEach((close) => close());
        });

        useBus(this.env.searchModel, "focus-view", () => {
            const { model } = this.props.list;
            if (model.useSampleModel || !model.hasData()) {
                return;
            }
            // Focus first kanban card
            rootRef.el.querySelector(".o_kanban_record").focus();
        });

        useHotkey(
            "Enter",
            ({ target }) => {
                if (!target.classList.contains("o_kanban_record")) {
                    return;
                }

                // Open first link
                const firstLink = target.querySelector("a, button");
                if (firstLink && firstLink instanceof HTMLElement) {
                    firstLink.click();
                }
                return;
            },
            { area: () => rootRef.el }
        );

        const arrowsOptions = { area: () => rootRef.el, allowRepeat: true };
        useHotkey(
            "ArrowUp",
            ({ area }) => {
                if (!this.focusNextCard(area, "up")) {
                    this.env.searchModel.trigger("focus-search");
                }
            },
            arrowsOptions
        );
        useHotkey("ArrowDown", ({ area }) => this.focusNextCard(area, "down"), arrowsOptions);
        useHotkey("ArrowLeft", ({ area }) => this.focusNextCard(area, "left"), arrowsOptions);
        useHotkey("ArrowRight", ({ area }) => this.focusNextCard(area, "right"), arrowsOptions);
    }

    // ------------------------------------------------------------------------
    // Getters
    // ------------------------------------------------------------------------

    get canMoveRecords() {
        if (!this.canResequenceRecords) {
            return false;
        }
        if (!this.props.list.groupByField) {
            return true;
        }
        const { groupByField } = this.props.list;
        const { modifiers, type } = groupByField;
        return Boolean(
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
        const { isGrouped, orderBy } = this.props.list;
        const { handleField, recordsDraggable } = this.props.archInfo;
        return Boolean(
            recordsDraggable &&
                (isGrouped || (handleField && (!orderBy[0] || orderBy[0].name === handleField)))
        );
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
            return list.records.map((record) => ({ record, key: record.id }));
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
        return !this.env.isSmall && isFolded ? `${name} (${count})` : name;
    }

    getGroupClasses(group) {
        const classes = [];
        if (this.canResequenceGroups && group.value) {
            classes.push("o_group_draggable");
        }
        if (!group.count) {
            classes.push("o_kanban_no_records");
        }
        if (!this.env.isSmall && group.isFolded) {
            classes.push("o_column_folded");
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
        const records = group.getAggregableRecords();
        return (progressBar ? progressBar.count : group.count) - records.length;
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
        return (
            activeActions.delete &&
            (!this.props.list.groupedBy || !this.props.list.groupedBy("m2m"))
        );
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
        const values = group.list.quickCreateRecord.data;
        let record;
        try {
            record = await group.validateQuickCreate();
        } catch (e) {
            // TODO: filter RPC errors more specifically (eg, for access denied, there is no point in opening a dialog)
            if (!(e instanceof RPCError)) {
                throw e;
            }
            const context = { ...group.context };
            context[`default_${group.groupByField.name}`] = group.value;
            context.default_name = values.name || values.display_name;
            // FIXME: since the new form view is not added to the registry yet, we
            // can't use the new FormViewDialog, as it would instantiate the legacy
            // form view. As a consequence, the control panel buttons would not be
            // moved to the footer.
            const adapterParent = standaloneAdapter({ Component });
            const dialog = new FormViewDialog(adapterParent, {
                res_model: this.props.list.resModel,
                context,
                title: this.env._t("Create"),
                disable_multiple_selection: true,
                on_saved: async (record) => {
                    await group.load();
                    this.props.list.quickCreate(group);
                    this.props.list.model.notify();
                },
                // on_closed: () => {
                //     this.props.list.quickCreate(group);
                // },
            });
            dialog.open();
            this.dialogClose.push(() => dialog.close());
            // this.dialogClose.push(
            //     this.dialog.add(
            //         FormViewDialog,
            //         {
            //             resModel: this.props.list.resModel,
            //             context,
            //             title: this.env._t("Create"),
            //             onRecordSaved: (record) => {
            //                 group.addRecord(record, 0);
            //             },
            //         },
            //         {
            //             onClose: () => {
            //                 this.props.list.quickCreate(group);
            //             },
            //         }
            //     )
            // );
        }

        if (record) {
            if (mode === "edit") {
                await this.props.openRecord(record, "edit");
            } else {
                await this.quickCreate(group);
            }
        }
    }

    toggleGroup(group) {
        return group.toggle();
    }

    loadMore(group) {
        return group.list.loadMore();
    }

    editGroup(group) {
        // FIXME: since the new form view is not added to the registry yet, we
        // can't use the new FormViewDialog, as it would instantiate the legacy
        // form view. As a consequence, the control panel buttons would not be
        // moved to the footer.
        const adapterParent = standaloneAdapter({ Component });
        const dialog = new FormViewDialog(adapterParent, {
            res_model: group.resModel,
            res_id: group.value,
            context: group.context,
            title: sprintf(this.env._t("Edit: %s"), group.displayName),
            on_saved: async () => {
                await this.props.list.load();
                this.props.list.model.notify();
            },
        });
        dialog.open();
        this.dialogClose.push(() => dialog.close());
        // this.dialogClose.push(
        //     this.dialog.add(FormViewDialog, {
        //         context: group.context,
        //         resId: group.value,
        //         resModel: group.resModel,
        //         title: sprintf(this.env._t("Edit: %s"), group.displayName),

        //         onRecordSaved: async () => {
        //             await this.props.list.load();
        //             this.props.list.model.notify();
        //         },
        //     })
        // );
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

    // ------------------------------------------------------------------------
    // Handlers
    // ------------------------------------------------------------------------

    onGroupClick(group) {
        if (!this.env.isSmall && group.isFolded) {
            group.toggle();
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
        const groups = isGrouped ? [...area.querySelectorAll(".o_kanban_group")] : [area];
        const cards = [...groups]
            .map((group) => [...group.querySelectorAll(".o_kanban_record")])
            .filter((group) => group.length);

        // Search current card position
        let iGroup;
        let iCard;
        for (iGroup = 0; iGroup < cards.length; iGroup++) {
            const i = cards[iGroup].indexOf(document.activeElement);
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

    tooltipAttributes(group) {
        if (!group.tooltip) {
            return {};
        }
        return {
            "data-tooltip-template": "web.KanbanGroupTooltip",
            "data-tooltip-info": JSON.stringify(group.tooltip),
        };
    }
}

KanbanRenderer.props = [
    "archInfo",
    "list",
    "openRecord",
    "readonly",
    "forceGlobalClick?",
    "noContentHelp?",
];
KanbanRenderer.components = {
    Dropdown,
    DropdownItem,
    KanbanAnimatedNumber,
    KanbanColumnQuickCreate,
    KanbanRecord,
    KanbanRecordQuickCreate,
};
KanbanRenderer.template = "web.KanbanRenderer";
