/** @odoo-module  */

import { formatDate } from "@web/core/l10n/dates";
import { useService } from '@web/core/utils/hooks';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillUpdateProps, status } from "@odoo/owl";

const { DateTime } = luxon;

export class ProjectMilestone extends Component {
    setup() {
        this.orm = useService('orm');
        this.dialog = useService("dialog");
        this.milestone = useState(this.props.milestone);
        this.state = useState({
            colorClass: this._getColorClass(),
            checkboxIcon: this._getCheckBoxIcon(),
        });
        onWillUpdateProps(this.onWillUpdateProps);
    }

    get resModel() {
        return 'project.milestone';
    }

    get deadline() {
        if (!this.milestone.deadline) return;
        return formatDate(DateTime.fromISO(this.milestone.deadline));
    }

    _getColorClass() {
        return this.milestone.is_deadline_exceeded && !this.milestone.can_be_marked_as_done ? "text-danger" : this.milestone.can_be_marked_as_done ? "text-success" : "";
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
        this.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure you want to delete this record?"),
            confirm: async () => {
                await this.orm.call('project.milestone', 'unlink', [this.milestone.id]);
                await this.props.load();
            },
            cancel: () => {},
        });
    }

    async onOpenMilestone() {
        if (!this.write_mutex) {
            this.write_mutex = true;
            this.props.open({
                resModel: this.resModel,
                resId: this.milestone.id,
                title: _t("Milestone"),
            }, {
                onClose: async () => {
                    if (status(this) === "mounted") {
                        await this.props.load();
                        this.write_mutex = false;
                    }
                },
            });
        }
    }

    async toggleIsReached() {
        if (!this.write_mutex) {
            this.write_mutex = true;
            this.milestone = await this.orm.call(
                this.resModel,
                'toggle_is_reached',
                [[this.milestone.id], !this.milestone.is_reached],
            );
            this.state.colorClass = this._getColorClass();
            this.state.checkboxIcon = this._getCheckBoxIcon();
            this.write_mutex = false;
        }
    }
}

ProjectMilestone.props = {
    context: Object,
    milestone: Object,
    open: Function,
    load: Function,
};
ProjectMilestone.template = 'project.ProjectMilestone';
