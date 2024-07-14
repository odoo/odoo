/** @odoo-module **/
import { onMounted, onWillStart, useState, Component, useSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { _t } from "@web/core/l10n/translation";
import { pyToJsLocale } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";

import { UNTITLED_SPREADSHEET_NAME } from "@spreadsheet/helpers/constants";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { DataSources } from "@spreadsheet/data_sources/data_sources";

import { loadSpreadsheetDependencies } from "@spreadsheet/assets_backend/helpers";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { SpreadsheetComponent } from "../spreadsheet_component";
import { SpreadsheetControlPanel } from "../control_panel/spreadsheet_control_panel";
import { SpreadsheetName } from "../control_panel/spreadsheet_name";
import { migrate } from "@spreadsheet/o_spreadsheet/migration";
import {
    useSpreadsheetCurrencies,
    useSpreadsheetLocales,
    useSpreadsheetThumbnail,
} from "../../hooks";
import { formatToLocaleString } from "../../helpers";

const { Model } = spreadsheet;

export class VersionHistoryAction extends Component {
    setup() {
        this.params = this.props.action.params;
        this.orm = useService("orm");
        this.router = useService("router");
        this.dialog = useService("dialog");
        this.actionService = useService("action");
        this.resId = this.params.spreadsheet_id || (this.props.state && this.props.state.resId); // used when going back to a spreadsheet via breadcrumb
        this.resModel = this.params.res_model || (this.props.state && this.props.state.remoModel); // used when going back to a spreadsheet via breadcrumb
        this.fromSnapshot =
            this.params.from_snapshot || (this.props.state && this.props.state.fromSnapshot);
        this.loadLocales = useSpreadsheetLocales();
        this.loadCurrencies = useSpreadsheetCurrencies();
        this.getThumbnail = useSpreadsheetThumbnail();

        useSubEnv({
            historyManager: {
                getRevisions: this.getRevisions.bind(this),
                forkHistory: this.forkHistory.bind(this),
                renameRevision: this.renameRevision.bind(this),
            },
        });

        this.state = useState({
            spreadsheetName: UNTITLED_SPREADSHEET_NAME,
            revisions: [],
            restorableRevisions: [],
        });

        onWillStart(async () => {
            await this.fetchData();
            this.createModel();
        });

        onMounted(() => {
            this.router.pushState({
                spreadsheet_id: this.resId,
                res_model: this.resModel,
                from_snapshot: this.fromSnapshot,
            });
            this.env.config.setDisplayName(this.state.spreadsheetName);

            /**
             * Do not copy this. We currently lack the ability to control the spreadsheet
             * sidepanel from outside `Spreadsheet` component. This is a temporary hack
             * */
            this.spreadsheetChildEnv = Object.values(
                Object.values(this.__owl__.children).find(
                    (el) => el.component.constructor.name === "SpreadsheetComponent"
                ).children
            ).find((el) => el.component.constructor.name === "Spreadsheet").childEnv;

            this.spreadsheetChildEnv.openSidePanel("VersionHistory", {
                onCloseSidePanel: async () => {
                    const action = await this.env.services.orm.call(this.resModel, "action_edit", [
                        this.resId,
                    ]);
                    this.env.services.action.doAction(action, {
                        clearBreadcrumbs: true,
                    });
                },
            });
        });
    }

    getRevisions() {
        return this.state.restorableRevisions;
    }

    async renameRevision(revisionId, name) {
        this.state.revisions.find((el) => el.id === revisionId).name = name;
        this.generateRestorableRevisions();
        await this.orm.call(this.resModel, "rename_revision", [this.resId, revisionId, name]);
    }

    async forkHistory(revisionId) {
        const data = this.model.exportData();
        const revision = this.state.revisions.find((rev) => rev.id === revisionId);
        data.revisionId = revision.nextRevisionId;
        const code = pyToJsLocale(this.model.getters.getLocale().code);
        const timestamp = formatToLocaleString(revision.timestamp, code);
        const name = _t("%(name)s (restored from %(timestamp)s)", {
            name: this.state.spreadsheetName,
            timestamp,
        });
        const defaultValues = {
            thumbnail: this.getThumbnail(),
            name,
        };
        const action = await this.orm.call(this.resModel, "fork_history", [this.resId], {
            revision_id: revisionId,
            spreadsheet_snapshot: data,
            default: defaultValues,
        });
        // Redirect to the forked spreadsheet
        this.actionService.doAction(action, { clearBreadcrumbs: true });
    }

    async fetchData() {
        const [spreadsheetHistoryData] = await Promise.all([
            this._fetchData(),
            loadSpreadsheetDependencies(),
        ]);
        this.spreadsheetData = spreadsheetHistoryData.data;
        this.state.revisions = spreadsheetHistoryData.revisions;
        this.generateRestorableRevisions();
        this.state.spreadsheetName = spreadsheetHistoryData.name;
        this.currentRevisionId =
            spreadsheetHistoryData.revisions.at(-1)?.nextRevisionId ||
            spreadsheetHistoryData.data.revisionId ||
            "START_REVISION";
        this.dataSources = new DataSources(this.env);
    }

    generateRestorableRevisions() {
        this.state.restorableRevisions = this.state.revisions
            .slice()
            .filter((el) => el.type !== "SNAPSHOT_CREATED")
            .reverse();
    }

    /**
     * @returns {Promise<SpreadsheetRecord>}
     */
    async _fetchData() {
        const record = await this.orm.call(this.resModel, "get_spreadsheet_history", [
            this.resId,
            !!this.fromSnapshot,
        ]);
        return record;
    }

    /**
     * @private
     */
    _resetDataSourcesBinds() {
        this.dataSources.removeEventListener(
            "data-source-updated",
            this._dataSourceBind.bind(this)
        );
        this.dataSources.addEventListener("data-source-updated", this._dataSourceBind.bind(this));
    }

    /**
     * @private
     */
    _dataSourceBind() {
        const sheetId = this.model.getters.getActiveSheetId();
        this.model.dispatch("EVALUATE_CELLS", { sheetId });
    }

    reloadFromSnapshot() {
        this.actionService.doAction(
            {
                type: "ir.actions.client",
                tag: this.props.action.tag,
                params: {
                    spreadsheet_id: this.resId,
                    res_model: this.resModel,
                    from_snapshot: true,
                },
            },
            { clearBreadcrumbs: true }
        );
    }

    async loadEditAction() {
        const action = await this.env.services.orm.call(this.resModel, "action_edit", [this.resId]);
        this.actionService.doAction(action, {
            clearBreadcrumbs: true,
        });
    }

    createModel() {
        this._resetDataSourcesBinds();
        const data = this.spreadsheetData;
        this.model = new Model(
            migrate(data),
            {
                custom: {
                    env: this.env,
                    orm: this.orm,
                    dataSources: this.dataSources,
                },
                external: {
                    loadCurrencies: this.loadCurrencies,
                    loadLocales: this.loadLocales,
                },
                mode: "readonly",
            },
            this.state.revisions
        );

        if (this.model.session.serverRevisionId !== this.currentRevisionId) {
            this.model = new Model({});
            if (!this.fromSnapshot) {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Odoo Spreadsheet"),
                    body: _t(
                        "There are missing revisions that prevent to restore the whole edition history.\n\
Would you like to load the more recent modifications?"
                    ),
                    confirm: () => {
                        this.reloadFromSnapshot();
                    },
                    close: () => {
                        this.loadEditAction();
                    },
                });
            } else {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Odoo Spreadsheet"),
                    body: _t(
                        "The history of your spreadsheet is corrupted and you are likely missing recent revisions. This feature cannot be used."
                    ),
                    confirm: () => {
                        this.loadEditAction();
                    },
                });
            }
        }
        if (this.env.debug) {
            // eslint-disable-next-line no-import-assign
            spreadsheet.__DEBUG__ = spreadsheet.__DEBUG__ || {};
            spreadsheet.__DEBUG__.model = this.model;
        }
    }
}

VersionHistoryAction.template = "spreadsheet_edition.VersionHistoryAction";
VersionHistoryAction.components = {
    SpreadsheetComponent,
    SpreadsheetControlPanel,
    SpreadsheetName,
};
VersionHistoryAction.props = { ...standardActionServiceProps };
registry.category("actions").add("action_open_spreadsheet_history", VersionHistoryAction, {
    force: true,
});
