/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { usePopover } from "@web/core/popover/popover_hook";
import { memoize } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { useDebounced } from "@web/core/utils/timing";
import { isNull, isRelational } from "@web/views/utils";
import { ColumnProgress } from "@web/views/view_components/column_progress";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

class KanbanHeaderTooltip extends Component {
    static template = "web.KanbanGroupTooltip";
}

export class KanbanHeader extends Component {
    static template = "web.KanbanHeader";
    static components = { ColumnProgress, Dropdown, DropdownItem };
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

    get group() {
        return this.props.group;
    }

    get groupName() {
        const { groupByField, count, displayName, isFolded } = this.group;
        let name = displayName;
        if (groupByField.type === "boolean") {
            name = name ? this.env._t("Yes") : this.env._t("No");
        } else if (!name) {
            if (
                isRelational(groupByField) ||
                groupByField.type === "date" ||
                groupByField.type === "datetime" ||
                isNull(name)
            ) {
                name = this.env._t("None");
            }
        }
        return !this.env.isSmall && isFolded ? `${name} (${count})` : name;
    }

    get groupAggregate() {
        const { sumField } = this.group.model.progressAttributes;
        const value = this.group.getAggregates(sumField && sumField.name);
        const title = sumField ? sumField.string : this.env._t("Count");
        return { value, title };
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

    // ------------------------------------------------------------------------
    // Edition methods
    // ------------------------------------------------------------------------

    archiveGroup() {
        this.dialog.add(ConfirmationDialog, {
            body: this.env._t(
                "Are you sure that you want to archive all the records from this column?"
            ),
            confirm: () => this.group.list.archive(),
            cancel: () => {},
        });
    }

    unarchiveGroup() {
        this.group.list.unarchive();
    }

    deleteGroup() {
        this.dialog.add(ConfirmationDialog, {
            body: this.env._t("Are you sure you want to delete this column?"),
            confirm: async () => {
                this.props.deleteGroup(this.group);
            },
            confirmLabel: this.env._t("Delete"),
            cancel: () => {},
        });
    }

    editGroup() {
        const { context, displayName, resModel, value } = this.group;
        this.props.dialogClose.push(
            this.dialog.add(FormViewDialog, {
                context,
                resId: value,
                resModel,
                title: sprintf(this.env._t("Edit: %s"), displayName),
                onRecordSaved: async () => {
                    await this.props.list.load();
                    this.props.list.model.notify();
                },
            })
        );
    }

    quickCreate(group) {
        this.props.quickCreateState.groupId = this.group.id;
    }

    toggleGroup() {
        return this.group.toggle();
    }

    // ------------------------------------------------------------------------
    // Permissions
    // ------------------------------------------------------------------------

    canArchiveGroup() {
        const { archiveGroup } = this.props.activeActions;
        const hasActiveField = "active" in this.group.fields;
        return archiveGroup && hasActiveField && this.group.groupByField.type !== "many2many";
    }

    canDeleteGroup() {
        const { deleteGroup } = this.props.activeActions;
        const { groupByField, value } = this.group;
        return deleteGroup && isRelational(groupByField) && value;
    }

    canEditGroup() {
        const { editGroup } = this.props.activeActions;
        const { groupByField, value } = this.group;
        return editGroup && isRelational(groupByField) && value;
    }

    canQuickCreate() {
        return this.props.canQuickCreate;
    }
}
