/** @odoo-module **/

import fieldUtils from 'web.field_utils';
import { ComponentAdapter, standaloneAdapter } from 'web.OwlCompatibility';
import { FormViewDialog } from 'web.view_dialogs';
import { useService } from "@web/core/utils/hooks";

const { Component, onWillUpdateProps, useState } = owl;

export class ProjectRightSidePanelComponent extends Component {
    setup() {
        super.setup();
        this.contextValue = {};
    }

    async openLegacyFormDialog(params) {
        const adapterParent = standaloneAdapter({ Component });
        const dialog = new FormViewDialog(adapterParent, {
            context: this.contextValue,
            res_id: false,
            ...params,
        });
        await dialog.open();
        return dialog;
    }
}
ProjectRightSidePanelComponent.components = { ComponentAdapter };

class MilestoneComponent extends ProjectRightSidePanelComponent {
    setup() {
        super.setup();
        this.contextValue = Object.assign({}, {
            'default_project_id': this.props.context.active_id,
        }, this.props.context);
    }

    async openLegacyFormDialog(params) {
        return super.openLegacyFormDialog({
            res_model: "project.milestone",
            on_saved: this.props.onMilestoneUpdate,
            ...params,
        });
    }
}

export class AddMilestone extends MilestoneComponent {
    onAddMilestoneClick(event) {
        event.stopPropagation();
        this.openLegacyFormDialog({
            _createContext: () => {
                return {
                    default_project_id: this.contextValue.active_id,
                    ...this.contextValue
                };
            },
            title: this.env._t("New Milestone"),
            multi_select: true
        });
    }
}
AddMilestone.template = 'project.AddMilestone';

export class OpenMilestone extends MilestoneComponent {

    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.milestone = useState(this.props.milestone);
        this.state = useState({
            colorClass: this._getColorClass(),
            checkboxIcon: this._getCheckBoxIcon(),
        });
        onWillUpdateProps(this.onWillUpdateProps);
    }

    get deadline() {
        return fieldUtils.format.date(moment(this.milestone.deadline));
    }

    _getColorClass() {
        return this.milestone.is_deadline_exceeded && !this.milestone.can_be_marked_as_done ? "o_milestone_danger" : this.milestone.can_be_marked_as_done ? "o_color_green" : "";
    }

    _getCheckBoxIcon() {
        return this.milestone.is_reached ? "fa-check-square-o" : "fa-square-o";
    }

    onWillUpdateProps(nextProps) {
        if (nextProps.milestone) {
            this.milestone = nextProps.milestone;
            this.state.colorClass = this._getColorClass();
            this.state.checkboxIcon = this._getCheckBoxIcon();
        }
        if (nextProps.context) {
            this.contextValue = nextProps.context;
        }
    }

    async onDeleteMilestone() {
        await this.rpc({
            model: 'project.milestone',
            method: 'unlink',
            args: [this.milestone.id]
        });
        await this.props.onMilestoneUpdate();
    }

    async onOpenMilestone() {
        if (!this.write_mutex) {
            this.write_mutex = true;
            const dialog = await this.openLegacyFormDialog({
                res_id: this.milestone.id,
                title: this.env._t("Milestone"),
                disable_multiple_selection: true,
                deletable: true
            });
            dialog.on('closed', this, () => {
                this.write_mutex = false;
            });
        }
    }

    async onMilestoneClick() {
        if (!this.write_mutex) {
            this.write_mutex = true;
            this.milestone = await this.rpc({
                model: 'project.milestone',
                method: 'toggle_is_reached',
                args: [[this.milestone.id], !this.milestone.is_reached],
            });
            this.state.colorClass = this._getColorClass();
            this.state.checkboxIcon = this._getCheckBoxIcon();
            this.write_mutex = false;
        }
    }
}
OpenMilestone.template = 'project.OpenMilestone';
