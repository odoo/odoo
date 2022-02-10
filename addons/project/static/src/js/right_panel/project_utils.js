/** @odoo-module **/

import { _lt } from 'web.core';
import fieldUtils from 'web.field_utils';
import { ComponentAdapter, standaloneAdapter } from 'web.OwlCompatibility';
import { FormViewDialog } from 'web.view_dialogs';

const { Component, onWillUpdateProps, useRef, useState } = owl;

class MilestoneComponent extends Component {
    setup() {
        super.setup();
        this.contextValue = Object.assign({}, {
            'default_project_id': this.props.context.active_id,
        }, this.props.context);
    }

    get context() {
        return this.contextValue;
    }

    set context(value) {
        this.contextValue = Object.assign({}, {
            'default_project_id': value.active_id,
        }, value);
    }

    async openLegacyFormDialog(params) {
        const adapterParent = standaloneAdapter({ Component });
        const dialog = new FormViewDialog(adapterParent, {
            context: this.context,
            res_model: "project.milestone",
            res_id: false,
            on_saved: this.props.onMilestoneUpdate,
            ...params,
        });
        await dialog.open();
        return dialog;
    }
}
MilestoneComponent.components = { ComponentAdapter };

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
        this.milestone = useState(this.props.milestone);
        this.state = useState({
            colorClass: this.milestone.is_deadline_exceeded ? "o_milestone_danger" : "",
            checkboxIcon: this.milestone.is_reached ? "fa-check-square-o" : "fa-square-o",
        });
        onWillUpdateProps(this.onWillUpdateProps);
    }

    get deadline() {
        return fieldUtils.format.date(moment(this.milestone.deadline));
    }

    onWillUpdateProps(nextProps) {
        if (nextProps.milestone) {
            this.milestone = nextProps.milestone;
            this.state.colorClass = this.milestone.is_deadline_exceeded ? "o_milestone_danger" : "";
            this.state.checkboxIcon = this.milestone.is_reached ? "fa-check-square-o" : "fa-square-o";
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
            this.state.colorClass = this.milestone.is_deadline_exceeded ? "o_milestone_danger" : "";
            this.state.checkboxIcon = this.milestone.is_reached ? "fa-check-square-o" : "fa-square-o";
            this.write_mutex = false;
        }
    }
}
OpenMilestone.template = 'project.OpenMilestone';
