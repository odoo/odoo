import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/views/fields/formatters";
import { ViewButton } from '@web/views/view_button/view_button';
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';

import { ProjectRightSidePanelSection } from './components/project_right_side_panel_section';
import { ProjectMilestone } from './components/project_milestone';
import { ProjectProfitability } from './components/project_profitability';
import { getCurrency } from '@web/core/currency';
import { Component, onWillStart, useState } from "@odoo/owl";
import { SIZES } from "@web/core/ui/ui_service";

export class ProjectRightSidePanel extends Component {
    static components = {
        ProjectRightSidePanelSection,
        ProjectMilestone,
        ViewButton,
        ProjectProfitability,
    };
    static template = "project.ProjectRightSidePanel";
    static props = {
        context: Object,
        domain: Array,
    };

    setup() {
        this.orm = useService('orm');
        this.actionService = useService('action');
        this.dialog = useService('dialog');
        this.uiService = useService("ui");
        useBus(this.uiService.bus, "resize", this.updateGridTemplateColumns)
        this.state = useState({
            data: {
                milestones: {
                    data: [],
                },
                profitability_items: {
                    costs: { data: [], total: { billed: 0.0, to_bill: 0.0 } },
                    revenues: { data: [], total: { invoiced: 0.0, to_invoice: 0.0 } },
                },
                user: {},
                currency_id: false,
            },
            gridTemplateColumns: this._getGridTemplateColumns(),
        });

        onWillStart(() => this.loadData());
    }

    _getGridTemplateColumns() {
        switch (this.uiService.size) {
            case SIZES.XS:
                return 2;
            case SIZES.VSM:
                return 3;
            case SIZES.XXL:
                return 6;
            default:
                return 4;
        }
    }

    updateGridTemplateColumns() {
        this.state.gridTemplateColumns = this._getGridTemplateColumns();
    }

    get panelVisible() {
        return this.state.data.show_milestones || this.state.data.show_project_profitability_helper;
    }

    get context() {
        return this.props.context;
    }

    get domain() {
        return this.props.domain;
    }

    get projectId() {
        return this.context.active_id;
    }

    get currencyId() {
        return this.state.data.currency_id;
    }

    get sectionNames() {
        return {
            'milestones': _t('Milestones'),
            'profitability': _t('Profitability'),
        };
    }

    get showProjectProfitability() {
        const { costs, revenues } = this.state.data.profitability_items;
        return costs.data.length || revenues.data.length;
    }

    formatFloat(value) {
        return formatFloat(value, { digits: [false, 1] });
    }

    formatMonetary(value, options = {}) {
        const valueFormatted = formatFloat(value, {
            ...options,
            'digits': [false, 0],
            'noSymbol': true,
        });
        const currency = getCurrency(this.currencyId);
        if (!currency) {
            return valueFormatted;
        }
        if (currency.position === "after") {
            return `${valueFormatted}\u00A0${currency.symbol}`;
        } else {
            return `${currency.symbol}\u00A0${valueFormatted}`;
        }
    }

    async loadData() {
        if (!this.projectId) { // If this is called from notif, multiples updates but no specific project
            return {};
        }
        const data = await this.orm.call(
            'project.project',
            'get_panel_data',
            [[this.projectId]],
            { context: this.context },
        );
        this.state.data = data;
        return data;
    }

    async loadMilestones() {
        const milestones = await this.orm.call(
            'project.project',
            'get_milestones',
            [[this.projectId]],
            { context: this.context },
        );
        this.state.data.milestones = milestones;
        return milestones;
    }

    addMilestone() {
        const context = {
            ...this.context,
            'default_project_id': this.projectId,
        };
        this.openFormViewDialog({
            context,
            title: _t('New Milestone'),
            resModel: 'project.milestone',
            onRecordSaved: async () => {
                await this.loadMilestones();
            },
        });
    }

    async openFormViewDialog(params, options = {}) {
        this.dialog.add(FormViewDialog, params, options);
    }

    async onProjectActionClick(params) {
        this.actionService.doActionButton({
            type: 'action',
            resId: this.projectId,
            context: this.context,
            resModel: 'project.project',
            ...params,
        });
    }

    _getStatButtonClickParams(statButton) {
        return {
            type: statButton.action_type,
            name: statButton.action,
            context: statButton.additional_context || '{}',
        };
    }

    _getStatButtonRecordParams() {
        return {
            resId: this.projectId,
            context: JSON.stringify(this.context),
            resModel: 'project.project',
        };
    }
}
