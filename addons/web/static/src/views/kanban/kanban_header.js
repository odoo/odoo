// @ts-check

/** @module @web/views/kanban/kanban_header - Column header with group title, record count, progress bar, and fold/edit/delete cog menu */

import { Component, useRef } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { utils } from "@web/ui/block/ui_service";
import { usePopover } from "@web/ui/popover/popover_hook";
import { GroupConfigMenu } from "@web/views/view_components/group_config_menu";

import { ColumnProgress } from "./column_progress";

/** Popover component displaying field-based tooltip info for a kanban group header. */
class KanbanHeaderTooltip extends Component {
    static template = "web.KanbanGroupTooltip";
    static props = {
        tooltip: Array,
        close: Function,
    };
}

/**
 * Header component for a kanban column (group).
 *
 * Renders the group title, record count, optional progress bar, cog menu
 * (fold/edit/delete/archive), tooltip on hover for many2one groups, and
 * quick-create trigger button.
 */
export class KanbanHeader extends Component {
    static template = "web.KanbanHeader";
    static components = {
        ColumnProgress,
        Dropdown,
        DropdownItem,
        GroupConfigMenu,
    };
    static props = {
        activeActions: { type: Object },
        canQuickCreate: { type: Boolean },
        deleteGroup: { type: Function },
        dialogClose: { type: Array },
        group: { type: Object },
        list: { type: Object },
        quickCreateState: { type: Object },
        scrollTop: { type: Function },
        tooltipInfo: { type: Object },
        progressBarState: { type: true, optional: true },
    };

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.rootRef = useRef("root");
        this.popover = usePopover(KanbanHeaderTooltip);
        this.onTitleMouseEnter = useDebounced(this.onTitleMouseEnter, 400);
    }

    /**
     * Show a tooltip popover on group title hover (debounced).
     * Only fires for many2one group-by fields that have tooltip info.
     * @param {MouseEvent} ev
     */
    async onTitleMouseEnter(ev) {
        if (!this.hasTooltip) {
            return;
        }
        const tooltip = await this.loadTooltip();
        if (tooltip.length) {
            this.popover.open(ev.target, { tooltip });
        }
    }

    /** Cancel pending tooltip load and close any open popover. */
    onTitleMouseLeave() {
        /** @type {any} */ (this.onTitleMouseEnter).cancel();
        this.popover.close();
    }

    // ------------------------------------------------------------------------
    // Getters
    // ------------------------------------------------------------------------

    /** @returns {Object} Props for the GroupConfigMenu dropdown (fold, edit, delete, archive). */
    get configMenuProps() {
        return {
            activeActions: this.props.activeActions,
            configItems: [
                [
                    "toggle_group",
                    {
                        label: _t("Fold"),
                        method: () => this.group.toggle(),
                        isVisible: () => !utils.isSmall(),
                        class: () => ({
                            o_kanban_toggle_fold: true,
                            disabled: this.props.list.model.useSampleModel,
                        }),
                        icon: "fa-compress",
                    },
                ],
                ...registry.category("group_config_items").getEntries(),
            ],
            deleteGroup: this.props.deleteGroup,
            dialogClose: this.props.dialogClose,
            group: this.props.group,
            list: this.props.list,
        };
    }

    /** @returns {Object | undefined} Progress bar info for this column, if enabled. */
    get progressBar() {
        return this.props.progressBarState?.getGroupInfo(this.group);
    }

    get group() {
        return this.props.group;
    }

    /** @returns {{ title: string, value: number }} Aggregate value for the progress bar sum field. */
    get groupAggregate() {
        const { group, progressBarState } = this.props;
        const { sumField } = progressBarState.progressAttributes;
        return progressBarState.getAggregateValue(group, sumField);
    }

    // ------------------------------------------------------------------------
    // Tooltip methods
    // ------------------------------------------------------------------------

    /** @returns {boolean} Whether this group header should show a tooltip on hover. */
    get hasTooltip() {
        const { name, type } = this.group.groupByField;
        return (
            type === "many2one" && this.group.value && name in this.props.tooltipInfo
        );
    }

    /**
     * Fetch tooltip field values from the server (memoized).
     * @returns {Promise<Array<{ title: string, value: any }>>}
     */
    loadTooltip = memoize(async () => {
        const { name, relation: resModel } = this.group.groupByField;
        const tooltipInfo = this.props.tooltipInfo[name];
        const fieldNames = Object.keys(tooltipInfo);
        const [values] = await this.orm.silent.read(
            resModel,
            [this.group.value],
            ["display_name", ...fieldNames],
        );

        return fieldNames
            .filter((fieldName) => values[fieldName])
            .map((fieldName) => ({
                title: tooltipInfo[fieldName],
                value: values[fieldName],
            }));
    });

    /** Activate quick-create mode for this column. */
    quickCreate(group) {
        this.props.quickCreateState.groupId = this.group.id;
    }

    /** Fold or unfold this column. */
    toggleGroup() {
        return this.group.toggle();
    }

    canQuickCreate() {
        return this.props.canQuickCreate;
    }

    /**
     * Handle a progress bar segment click to filter the column.
     * @param {*} value - The bar value that was clicked.
     */
    async onBarClicked(value) {
        await this.props.progressBarState.selectBar(this.props.group.id, value);
        this.props.scrollTop();
    }
}
