/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { MrpMpsControlPanel, MrpMpsSearchBar } from "../search/mrp_mps_control_panel";
import { MrpMpsSearchModel } from '../search/mrp_mps_search_model';
import MpsLineComponent from '@mrp_mps/components/line';
import { MasterProductionScheduleModel } from '@mrp_mps/models/master_production_schedule_model';
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { usePager } from "@web/search/pager_hook";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import { WithSearch } from "@web/search/with_search/with_search";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { download } from "@web/core/network/download";
import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";
import { Component, onWillStart, useSubEnv } from "@odoo/owl";

class MainComponent extends Component {
    //--------------------------------------------------------------------------
    // Lifecycle
    //--------------------------------------------------------------------------
    setup() {
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.viewService = useService("view");
        this.rpc = useService("rpc");

        const { orm, action, dialog } = this;
        this.model = new MasterProductionScheduleModel(this.props, { orm, action, dialog });
        this.withSearchProps = null;

        useSubEnv({
            manufacturingPeriods: [],
            model: this.model,
            defaultPageLimit: 20,
            config: {
                ...this.env.config,
                offset: 0,
                limit: 20,
                mpsImportRecords: true,
            },
        });

        useSetupAction({
            getContext: () => {
                return this.props.action.context;
            },
        });

        useBus(this.model, "update", () => this.render(true));

        onWillStart(async () => {
            this.env.config.setDisplayName(_t("Master Production Schedule"));
            this.withSearchProps = await this._prepareWithSearchProps();
            const domain = this.props.action.domain;
            await this.model.load(domain, this.env.config.offset, this.env.config.limit);
        });

        usePager(() => {
            return {
                offset: this.env.config.offset,
                limit: this.env.config.limit,
                total: this.model.data.count,
                onUpdate: async ({ offset, limit }) => {
                    this.env.config.offset = offset;
                    this.env.config.limit = limit;
                    this.model.load(undefined, offset, limit);
                },
            };
        });
    }

    async _prepareWithSearchProps() {
        const views = await this.viewService.loadViews(
            {
                resModel: "mrp.production.schedule",
                context: this.props.action.context,
                views: [[false, "search"]],
            }
        );
        return {
            SearchModel: MrpMpsSearchModel,
            resModel: "mrp.production.schedule",
            context: this.props.action.context,
            orderBy: [{name: "id", asc: true}],
            searchMenuTypes: ['filter', 'favorite'],
            searchViewArch: views.views.search.arch,
            searchViewId: views.views.search.id,
            searchViewFields: views.fields,
            loadIrFilters: true
        };
    }

    get lines() {
        return this.model.data.production_schedule_ids;
    }

    get manufacturingPeriods() {
        return this.model.data.dates;
    }

    get groups() {
        return this.model.data.groups[0];
    }

    get isSelected() {
        return this.model.selectedRecords.size === this.lines.length;
    }

    toggleSelection() {
        this.model.toggleSelection();
    }

    /**
     * Handles the click on replenish button. It will call action_replenish with
     * all the Ids present in the view.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickReplenish(ev) {
        this.model.replenishAll();
    }

    _onMouseOverReplenish(ev) {
        this.model.mouseOverReplenish();
    }

    _onMouseOutReplenish(ev) {
        this.model.mouseOutReplenish();
    }

    _onClickCreate(ev) {
        this.model._createProduct();
    }

    get actionMenuItems() {
        return {
            action: [
                {
                    key: "export",
                    description: _t("Export"),
                    callback: () => this.onExportData(),
                },
                {
                    key: "delete",
                    description: _t("Delete"),
                    callback: () => this.unlinkSelectedRecord(),
                },
                {
                    key: "replenish",
                    description: _t("Replenish"),
                    callback: () => this.replenishSelectedRecords(),
                },
            ],
        };
    }

    get isRecordSelected() {
        return this.model.selectedRecords.size > 0;
    }

    replenishSelectedRecords() {
        this.model.replenishSelectedRecords();
    }

    unlinkSelectedRecord() {
        this.model.unlinkSelectedRecord();
    }

    async getExportedFields(model, import_compat, parentParams) {
        return await this.rpc("/web/export/get_fields", {
            ...parentParams,
            model,
            import_compat,
        });
    }

    async downloadExport(fields, import_compat, format) {
        const resIds = Array.from(this.model.selectedRecords);
        const exportedFields = fields.map((field) => ({
            name: field.name || field.id,
            label: field.label || field.string,
            store: field.store,
            type: field.field_type,
        }));
        if (import_compat) {
            exportedFields.unshift({ name: "id", label: _t("External ID") });
        }
        await download({
            data: {
                data: JSON.stringify({
                    import_compat,
                    context: this.props.context,
                    domain: this.model.domain,
                    fields: exportedFields,
                    ids: resIds.length > 0 && resIds,
                    model: "mrp.production.schedule",
                }),
            },
            url: `/web/export/${format}`,
        });
    }

    /**
     * Opens the Export Dialog
     *
     * @private
     */
    onExportData() {
        const dialogProps = {
            context: this.props.context,
            defaultExportList: [],
            download: this.downloadExport.bind(this),
            getExportedFields: this.getExportedFields.bind(this),
            root: {
                resModel: "mrp.production.schedule",
                activeFields: [],
            },
        };
        this.dialog.add(ExportDataDialog, dialogProps);
    }
}

MainComponent.template = 'mrp_mps.mrp_mps';
MainComponent.components = {
    MrpMpsControlPanel,
    WithSearch,
    MpsLineComponent,
    CheckBox,
    MrpMpsSearchBar,
    ActionMenus,
};

registry.category("actions").add("mrp_mps_client_action", MainComponent);

export default MainComponent;
