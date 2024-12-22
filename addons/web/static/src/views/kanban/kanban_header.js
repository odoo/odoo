/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, useRef } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { usePopover } from "@web/core/popover/popover_hook";
import { memoize } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { isRelational } from "@web/model/relational_model/utils";
import { isNull } from "@web/views/utils";
import { ColumnProgress } from "@web/views/view_components/column_progress";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { registry } from "@web/core/registry";
import { utils } from "@web/core/ui/ui_service";

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

    get _configDropdownContainer() {
        // FIXME: please do not override this getter in other modules.
        // The dropdown's container prop is only used here as a workaround of
        // a stacking context issue. It should be removed in the next release.
        return this.rootRef.el.closest(`.o_kanban_group[data-id="${this.props.group.id}"]`);
    }

    get configItems() {
        const args = { permissions: this.permissions, props: this.props };
        return registry
            .category("kanban_header_config_items")
            .getEntries()
            .map(([key, desc]) => ({
                key,
                method: desc.method,
                label: desc.label,
                isVisible:
                    typeof desc.isVisible === "function" ? desc.isVisible(args) : desc.isVisible,
                class: typeof desc.class === "function" ? desc.class(args) : desc.class,
            }));
    }

    get progressBar() {
        return this.props.progressBarState?.getGroupInfo(this.group);
    }

    get group() {
        return this.props.group;
    }

    _getEmptyGroupLabel(fieldName) {
        return _t("None");
    }

    get groupName() {
        const { groupByField, displayName } = this.group;
        let name = displayName;
        if (groupByField.type === "boolean") {
            name = name ? _t("Yes") : _t("No");
        } else if (!name) {
            if (
                isRelational(groupByField) ||
                groupByField.type === "date" ||
                groupByField.type === "datetime" ||
                isNull(name)
            ) {
                name = this._getEmptyGroupLabel(groupByField.name);
            }
        }
        return name;
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

    // ------------------------------------------------------------------------
    // Edition methods
    // ------------------------------------------------------------------------

    archiveGroup() {
        this.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure that you want to archive all the records from this column?"),
            confirmLabel: _t("Archive All"),
            confirm: () => this.group.list.archive(),
            cancel: () => {},
        });
    }

    unarchiveGroup() {
        this.group.list.unarchive();
    }

    deleteGroup() {
        this.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure you want to delete this column?"),
            confirm: async () => {
                this.props.deleteGroup(this.group);
            },
            confirmLabel: _t("Delete"),
            cancel: () => {},
        });
    }

    editGroup() {
        const { context, displayName, groupByField, value } = this.group;
        this.props.dialogClose.push(
            this.dialog.add(FormViewDialog, {
                context,
                resId: value,
                resModel: groupByField.relation,
                title: _t("Edit: %s", displayName),
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

    get permissions() {
        return ["canArchiveGroup", "canDeleteGroup", "canEditGroup", "canQuickCreate"].reduce(
            (o, key) => {
                Object.defineProperty(o, key, { get: () => this[key]() });
                return o;
            },
            {}
        );
    }

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

    async onBarClicked(value) {
        await this.props.progressBarState.selectBar(this.props.group.id, value);
        this.props.scrollTop();
    }
}

const kanbanHeaderConfigItems = registry.category("kanban_header_config_items");
kanbanHeaderConfigItems.add(
    "toggle_group",
    {
        label: _t("Fold"),
        method: "toggleGroup",
        isVisible: () => !utils.isSmall(),
        class: ({ props }) => ({
            o_kanban_toggle_fold: true,
            disabled: props.list.model.useSampleModel,
        }),
    },
    { sequence: 10 }
);
kanbanHeaderConfigItems.add(
    "edit_group",
    {
        label: _t("Edit"),
        method: "editGroup",
        isVisible: ({ permissions }) => permissions.canEditGroup,
        class: "o_column_edit",
    },
    { sequence: 20 }
);
kanbanHeaderConfigItems.add(
    "delete_group",
    {
        label: _t("Delete"),
        method: "deleteGroup",
        isVisible: ({ permissions }) => permissions.canDeleteGroup,
        class: "o_column_delete",
    },
    { sequence: 30 }
);
kanbanHeaderConfigItems.add(
    "archive_group",
    {
        label: _t("Archive All"),
        method: "archiveGroup",
        isVisible: ({ permissions }) => permissions.canArchiveGroup,
        class: "o_column_archive_records",
    },
    { sequence: 40 }
);
kanbanHeaderConfigItems.add(
    "unarchive_group",
    {
        label: _t("Unarchive All"),
        method: "unarchiveGroup",
        isVisible: ({ permissions }) => permissions.canArchiveGroup,
        class: "o_column_unarchive_records",
    },
    { sequence: 50 }
);
