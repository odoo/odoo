import { Component, useRef } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { registry } from "@web/core/registry";
import { utils } from "@web/core/ui/ui_service";
import { memoize } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { ColumnProgress } from "@web/views/view_components/column_progress";
import { GroupConfigMenu } from "@web/views/view_components/group_config_menu";

class KanbanHeaderTooltip extends Component {
    static template = "web.KanbanGroupTooltip";
    static props = {
        tooltip: Array,
        close: Function,
    };
}

export class KanbanHeader extends Component {
    static template = "web.KanbanHeader";
    static components = { ColumnProgress, Dropdown, DropdownItem, GroupConfigMenu };
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

    async onTitleMouseEnter(ev) {
        if (!this.hasTooltip) {
            return;
        }
        const tooltip = await this.loadTooltip();
        if (tooltip.length) {
            this.popover.open(ev.target, { tooltip });
        }
    }

    onTitleMouseLeave() {
        this.onTitleMouseEnter.cancel();
        this.popover.close();
    }

    // ------------------------------------------------------------------------
    // Getters
    // ------------------------------------------------------------------------

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

    get progressBar() {
        return this.props.progressBarState?.getGroupInfo(this.group);
    }

    get group() {
        return this.props.group;
    }

    get groupAggregate() {
        const { group, progressBarState } = this.props;
        const { sumField } = progressBarState.progressAttributes;
        return progressBarState.getAggregateValue(group, sumField);
    }

    // ------------------------------------------------------------------------
    // Tooltip methods
    // ------------------------------------------------------------------------

    get hasTooltip() {
        const { name, type } = this.group.groupByField;
        return type === "many2one" && this.group.value && name in this.props.tooltipInfo;
    }

    loadTooltip = memoize(async () => {
        const { name, relation: resModel } = this.group.groupByField;
        const tooltipInfo = this.props.tooltipInfo[name];
        const fieldNames = Object.keys(tooltipInfo);
        const [values] = await this.orm.silent.read(
            resModel,
            [this.group.value],
            ["display_name", ...fieldNames]
        );

        return fieldNames
            .filter((fieldName) => values[fieldName])
            .map((fieldName) => ({ title: tooltipInfo[fieldName], value: values[fieldName] }));
    });

    quickCreate(group) {
        this.props.quickCreateState.groupId = this.group.id;
    }

    toggleGroup() {
        return this.group.toggle();
    }

    canQuickCreate() {
        return this.props.canQuickCreate;
    }

    async onBarClicked(value) {
        await this.props.progressBarState.selectBar(this.props.group.id, value);
        this.props.scrollTop();
    }
}
