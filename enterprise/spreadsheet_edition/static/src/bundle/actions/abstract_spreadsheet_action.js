import { _t } from "@web/core/l10n/translation";
import {
    onMounted,
    onWillStart,
    useState,
    Component,
    useSubEnv,
    onWillUnmount,
    useExternalListener,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/search/action_hook";
import { downloadFile } from "@web/core/network/download";
import { user } from "@web/core/user";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import { UNTITLED_SPREADSHEET_NAME, DEFAULT_LINES_NUMBER } from "@spreadsheet/helpers/constants";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { initCallbackRegistry } from "@spreadsheet/o_spreadsheet/init_callbacks";
import { RecordFileStore } from "../image/record_file_store";
import { useSpreadsheetCurrencies, useSpreadsheetLocales, useSpreadsheetThumbnail } from "../hooks";
import { useSpreadsheetPrint } from "@spreadsheet/hooks";
import { InputDialog } from "./input_dialog/input_dialog";
import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import { CommentsStore } from "../comments/comments_store";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { createDefaultCurrency } from "@spreadsheet/currency/helpers";

import { SpreadsheetNavbar } from "@spreadsheet_edition/bundle/components/spreadsheet_navbar/spreadsheet_navbar";
import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";

const uuidGenerator = new spreadsheet.helpers.UuidGenerator();

const { Model } = spreadsheet;
const { useStoreProvider, ModelStore, SidePanelStore } = spreadsheet.stores;

/**
 * @typedef SpreadsheetData
 * @property {number} id
 * @property {string} name
 * @property {string} data
 * @property {Object[]} revisions
 * @property {boolean} snapshot_requested
 * @property {Boolean} isReadonly
 * @property {string} [writable_rec_name_field]
 */

export class AbstractSpreadsheetAction extends Component {
    static template = "";
    static props = { ...standardActionServiceProps };
    static components = {
        SpreadsheetComponent,
        SpreadsheetNavbar,
    };
    static target = "fullscreen";

    setup() {
        if (!this.props.action.params) {
            // the action is coming from a this.trigger("do-action", ... ) of owl (not wowl and not legacy)
            this.params = this.props.action.context;
        } else {
            // the action is coming from wowl
            this.params = this.props.action.params;
        }
        this.isEmptySpreadsheet = this.params.is_new_spreadsheet || false;
        this.resId =
            this.params.resId ||
            this.params.spreadsheet_id || // backward compatibility. res_id used to be spreadsheet_id
            this.params.active_id || // backward compatibility. spreadsheet_id used to be active_id
            (this.props.state && this.props.state.resId); // used when going back to a spreadsheet via breadcrumb
        this.shareId = this.params.share_id || this.props.state?.shareId;
        this.accessToken = this.params.access_token || this.props.state?.accessToken;
        this.actionService = useService("action");
        this.notifications = useService("notification");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.http = useService("http");
        this.ui = useService("ui");
        this.loadLocales = useSpreadsheetLocales();
        this.loadCurrencies = useSpreadsheetCurrencies();
        this.getThumbnail = useSpreadsheetThumbnail();
        this.fileStore = new RecordFileStore(this.resModel, this.resId, this.http, this.orm);
        this.spreadsheetService = useService("spreadsheet_collaborative");
        this.stores = useStoreProvider();
        this.threadId = this.params?.thread_id;
        useSetupAction({
            beforeLeave: this._leaveSpreadsheet.bind(this),
            beforeUnload: this._leaveSpreadsheet.bind(this),
            getLocalState: () => {
                return {
                    resId: this.resId,
                    shareId: this.shareId,
                    accessToken: this.accessToken,
                    data: this.data,
                    model: this.model,
                };
            },
        });

        const print = useSpreadsheetPrint(() => this.model);
        useSubEnv({
            download: this.download.bind(this),
            downloadAsJson: this.downloadAsJson.bind(this),
            showHistory: this.showHistory.bind(this),
            insertThreadInSheet: this.insertThreadInSheet.bind(this),
            print,
            getLinesNumber: this._getLinesNumber.bind(this),
            getUserLocale: () => this.data && this.data.user_locale,
        });
        this.state = useState({
            spreadsheetName: UNTITLED_SPREADSHEET_NAME,
        });

        onWillStart(async () => {
            if (this.props.state?.model && this.props.state?.data) {
                this._initializeWith(this.props.state.data);
                this.model = this.props.state.model;
                this.model.joinSession();
                this.stores.inject(ModelStore, this.model);
            } else {
                await this.fetchData();
                this.createModel();
                this.stores.inject(ModelStore, this.model);
            }
        });
        onMounted(() => {
            this.execInitCallbacks();
            const commentsStore = this.stores.get(CommentsStore);
            this.props.updateActionState({
                resId: this.resId,
                access_token: this.accessToken,
                share_id: this.shareId,
            });
            this.env.config.setDisplayName(this.state.spreadsheetName);
            this.model.on("unexpected-revision-id", this, this.onUnexpectedRevisionId.bind(this));
            if (this.threadId) {
                // necessary atm - we need at least one frame to have the right viewport height/width
                setTimeout(() => commentsStore.openCommentThread(this.threadId), 0);
                const sidePanel = this.stores.get(SidePanelStore);
                sidePanel.open("Comments");
            }
        });
        onWillUnmount(() => {
            this.model.off("unexpected-revision-id", this);
        });
        useExternalListener(window, "afterprint", this.logExport.bind(this));
    }

    get navbarProps() {
        return {
            isReadonly: this.isReadonly,
            onSpreadsheetNameChanged: this._onSpreadSheetNameChanged.bind(this),
            spreadsheetName: this.state.spreadsheetName,
        };
    }

    async fetchData() {
        // if we are returning to the spreadsheet via the breadcrumb, we don't want
        // to do all the "creation" options of the actions
        if (!this.props.state) {
            await this._setupPreProcessingCallbacks();
        }
        const data = await this._fetchData();
        this._initializeWith(data);
    }

    createModel() {
        this.model = new Model(
            this.spreadsheetData,
            this.getModelConfig(),
            this.stateUpdateMessages
        );
        if (this.env.debug) {
            // eslint-disable-next-line no-import-assign
            spreadsheet.__DEBUG__ = spreadsheet.__DEBUG__ || {};
            spreadsheet.__DEBUG__.model = this.model;
        }
    }

    getModelConfig() {
        const transportService = this.spreadsheetService.makeCollaborativeChannel(
            this.resModel,
            this.resId,
            this.shareId,
            this.accessToken
        );
        const odooDataProvider = new OdooDataProvider(this.env);
        odooDataProvider.addEventListener("data-source-updated", () => {
            this.model.dispatch("EVALUATE_CELLS");
        });
        return {
            custom: { env: this.env, orm: this.orm, odooDataProvider },
            external: {
                fileStore: this.fileStore,
                loadCurrencies: this.loadCurrencies,
                loadLocales: this.loadLocales,
            },
            defaultCurrency: createDefaultCurrency(this.data.default_currency),
            transportService,
            client: {
                id: uuidGenerator.uuidv4(),
                name: user.name,
                userId: user.userId,
            },
            mode: this.isReadonly ? "readonly" : "normal",
            snapshotRequested: this.snapshotRequested,
            customColors: this.data.company_colors,
        };
    }

    async execInitCallbacks() {
        if (!this.props.state?.model || !this.props.state?.data) {
            if (this.asyncInitCallback) {
                try {
                    this.ui.block();
                    await this.asyncInitCallback(this.model, this.stores);
                } finally {
                    this.ui.unblock();
                }
            }
            if (this.initCallback) {
                this.initCallback(this.model, this.stores);
            }
        }
    }

    async _setupPreProcessingCallbacks() {
        if (this.params.preProcessingAction) {
            const initCallbackGenerator = initCallbackRegistry
                .get(this.params.preProcessingAction)
                .bind(this);
            this.initCallback = await initCallbackGenerator(this.params.preProcessingActionData);
        }
        if (this.params.preProcessingAsyncAction) {
            const initCallbackGenerator = initCallbackRegistry
                .get(this.params.preProcessingAsyncAction)
                .bind(this);
            this.asyncInitCallback = await initCallbackGenerator(
                this.params.preProcessingAsyncActionData
            );
        }
    }

    /**
     * @protected
     * @abstract
     * @param {SpreadsheetData} data
     */
    _initializeWith(data) {
        this.state.spreadsheetName = data.name;
        this.spreadsheetData = data.data;
        this.stateUpdateMessages = data.revisions;
        this.snapshotRequested = data.snapshot_requested;
        this.isReadonly = data.isReadonly;
        this.data = data;
    }

    /**
     * Make a copy of the current document
     * @protected
     */
    async makeCopy() {
        const display_thumbnail = this.getThumbnail();
        const data = this.model.exportData();
        const defaultValues = {
            spreadsheet_data: JSON.stringify(data),
            spreadsheet_snapshot: false,
            spreadsheet_revision_ids: [],
            display_thumbnail,
        };
        const ids = await this.orm.call(this.resModel, "copy", [[this.resId]], {
            default: defaultValues,
        });
        const id = ids[0];
        this._openSpreadsheet(id);
    }

    logExport() {
        this.model.dispatch("LOG_DATASOURCE_EXPORT", { action: "print" });
    }

    /**
     * @private
     */
    async _leaveSpreadsheet() {
        await this.model.leaveSession();
        this.model.off("update", this);
        if (!this.isReadonly) {
            return this.onSpreadsheetLeft();
        }
    }

    async _onSpreadSheetNameChanged(detail) {
        const { name } = detail;
        if (name && name !== this.state.spreadsheetName) {
            this.state.spreadsheetName = name;
            this.data.name = name;
            this.env.config.setDisplayName(this.state.spreadsheetName);
            if (this.data.writable_rec_name_field) {
                await this.orm.write(this.resModel, [this.resId], {
                    [this.data.writable_rec_name_field]: name,
                });
            }
        }
    }

    async createNewSpreadsheet() {
        throw new Error("not implemented by children");
    }

    async onSpreadsheetLeft() {
        if (this.accessToken) {
            return;
        }
        await this.orm.write(this.resModel, [this.resId], this.onSpreadsheetLeftUpdateVals());
    }

    onSpreadsheetLeftUpdateVals() {
        return { display_thumbnail: this.getThumbnail() };
    }

    /**
     * @returns {Promise<SpreadsheetData>}
     */
    async _fetchData() {
        return this.orm.call(this.resModel, "join_spreadsheet_session", [
            this.resId,
            this.accessToken,
        ]);
    }

    /**
     * @protected
     */
    _notifyCreation() {
        this.notifications.add(this.notificationMessage, {
            type: "info",
            sticky: false,
        });
    }

    /**
     * Open a spreadsheet
     * @private
     */
    _openSpreadsheet(spreadsheetId) {
        this._notifyCreation();
        this.actionService.doAction(
            {
                type: "ir.actions.client",
                tag: this.props.action.tag,
                params: { spreadsheet_id: spreadsheetId },
            },
            { clear_breadcrumbs: true }
        );
    }

    showHistory() {
        this.actionService.doAction(
            {
                type: "ir.actions.client",
                tag: "action_open_spreadsheet_history",
                params: {
                    spreadsheet_id: this.resId,
                    res_model: this.resModel,
                },
            },
            { clear_breadcrumbs: true }
        );
    }

    /**
     * Reload the spreadsheet if an unexpected revision id is triggered.
     */
    onUnexpectedRevisionId() {
        this.actionService.doAction("reload_context");
    }

    /**
     * Downloads the spreadsheet in xlsx format
     */
    async download() {
        this.ui.block();
        try {
            await waitForDataLoaded(this.model);
            const sources = this.model.getters.getLoadedDataSources();
            await this.actionService.doAction({
                type: "ir.actions.client",
                tag: "action_download_spreadsheet",
                params: {
                    name: this.state.spreadsheetName,
                    xlsxData: this.model.exportXLSX(),
                    sources,
                },
            });
        } finally {
            this.ui.unblock();
        }
    }

    /**
     * Downloads the spreadsheet in json format
     */
    async downloadAsJson() {
        this.ui.block();
        try {
            const data = JSON.stringify(this.model.exportData());
            await downloadFile(
                data,
                `${this.state.spreadsheetName}.osheet.json`,
                "application/json"
            );
        } finally {
            this.ui.unblock();
        }
    }

    _getLinesNumber(callback) {
        this.dialog.add(InputDialog, {
            body: _t("Select the number of records to insert"),
            confirm: callback,
            title: _t("Re-insert list"),
            inputValue: DEFAULT_LINES_NUMBER,
            inputType: "number",
        });
    }

    async insertThreadInSheet({ sheetId, col, row }) {
        const [threadId] = await this.env.services.orm.create("spreadsheet.cell.thread", [
            { [this.threadField]: this.resId },
        ]);
        this.model.dispatch("ADD_COMMENT_THREAD", {
            sheetId,
            col,
            row,
            threadId,
        });
        return threadId;
    }
}
