import { Component, onWillStart, useRef, useState } from "@odoo/owl";
import { useDropzone } from "@web/core/dropzone/dropzone_hook";
import { FileInput } from "@web/core/file_input/file_input";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useFileUploader } from "@web/core/utils/files";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { DocumentationLink } from "@web/views/widgets/documentation_link/documentation_link";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { ImportDataContent } from "../import_data_content/import_data_content";
import { ImportDataProgress } from "../import_data_progress/import_data_progress";
import { ImportDataSidepanel } from "../import_data_sidepanel/import_data_sidepanel";
import { useImportModel } from "../import_model";

export class ImportAction extends Component {
    static template = "ImportAction";
    static nextId = 1;
    static components = {
        FileInput,
        ImportDataContent,
        ImportDataSidepanel,
        Layout,
        DocumentationLink,
    };
    static props = { ...standardActionServiceProps };
    static path = "import";
    static displayName = _t("Import a File");

    setup() {
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.env.config.setDisplayName(this.props.action.name || _t("Import a File"));
        this.model = useImportModel({
            env: this.env,
            context: this.props.action.params?.context || {},
        });

        this.state = useState({
            filename: undefined,
            numRows: 0,
            importMessages: [],
            importProgress: {
                value: 0,
                step: 1,
            },
            isPaused: false,
            isTested: false,
            previewError: "",
        });

        this.uploadFiles = useFileUploader();
        useDropzone(useRef("root"), async (event) => {
            const { files } = event.dataTransfer;
            if (files.length === 0) {
                this.notification.add(
                    _t("Please upload an Excel (.xls or .xlsx) or .csv file to import."),
                    {
                        type: "danger",
                    }
                );
            } else if (files.length > 1) {
                this.notification.add(_t("Please upload a single file."), {
                    type: "danger",
                });
            } else {
                const file = files[0];
                const isValidFile =
                    file.name.endsWith(".csv") ||
                    file.name.endsWith(".xls") ||
                    file.name.endsWith(".xlsx");
                if (!isValidFile) {
                    this.notification.add(
                        _t("Please upload an Excel (.xls or .xlsx) or .csv file to import."),
                        {
                            type: "danger",
                        }
                    );
                } else {
                    await this.uploadFiles(this.uploadFilesRoute, {
                        csrf_token: odoo.csrf_token,
                        ufile: [file],
                        model: this.resModel,
                        id: this.model.id,
                    });
                    this.handleFilesUpload([file]);
                }
            }
        });

        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        const action = await this.actionService.currentAction;
        // this.props.action.params.model is there for retro-compatiblity issues
        const activeModel =
            this.props.action.params?.model || this.props.action.params?.active_model;
        if (activeModel) {
            this.resModel = activeModel;
            if (action?.type === "ir.actions.act_window" && action?.res_model === this.resModel) {
                this.action = action;
            } else {
                this.props.updateActionState({ active_model: this.resModel });
            }
        } else {
            if (!action) {
                return this.env.config.historyBack();
            }
            if (action.type !== "ir.actions.act_window") {
                return this.actionService.restore(this.actionService.currentController.jsId);
            }
            this.action = action;
            this.resModel = this.action.res_model;
        }
        this.model.setResModel(this.resModel);
        return this.model.init();
    }

    cancel() {
        this.env.config.historyBack();
    }

    openRecords(resIds) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Imported records"),
            res_model: this.model.resModel,
            view_mode: this.action?.view_mode || "list,form",
            views: this.action?.views || [
                [false, "list"],
                [false, "form"],
            ],
            domain: [["id", "in", resIds]],
            target: "current",
            path: "imported-records",
        });
    }

    get display() {
        return {
            controlPanel: {},
        };
    }

    get importTemplates() {
        return this.model.importTemplates;
    }

    get uploadFilesRoute() {
        return "/base_import/set_file";
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    get formattingOptions() {
        return this.model.formattingOptions;
    }

    get totalToImport() {
        return this.state.numRows - parseInt(this.importOptions.skip);
    }

    get totalSteps() {
        return this.isBatched ? Math.ceil(this.totalToImport / this.importOptions.limit) : 1;
    }

    get importOptions() {
        return this.model.importOptions;
    }

    get isPreviewing() {
        return this.state.filename !== undefined;
    }

    // Activate the batch configuration panel only if the number of rows > 100. (In order to let the user choose
    // the batch size even for medium size file. Could be useful to reduce the batch size for complex models).
    get isBatched() {
        return this.state.numRows > 100;
    }

    async onOptionChanged(name, value, fieldName = null) {
        this.model.block();
        const result = await this.model.setOption(name, value, fieldName);
        if (result) {
            const { res, error } = result;
            if (!error && res.num_rows) {
                this.state.numRows = res.num_rows;
                this.state.previewError = undefined;
            } else {
                this.state.previewError = error;
            }
        }
        this.model.unblock();
    }

    async reload() {
        this.model.block();
        await this.model.updateData();
        this.model.unblock();
    }

    //--------------------------------------------------------------------------
    // File
    //--------------------------------------------------------------------------

    async handleFilesUpload(files) {
        if (!files || files.length <= 0) {
            return;
        }

        this.state.filename = files[0].name;
        this.state.importMessages = [];

        this.model.block(_t("Loading file..."));
        const { res, error } = await this.model.updateData(true);

        if (error) {
            this.state.previewError = error;
        } else {
            this.state.numRows = res.num_rows;
            this.state.previewError = undefined;
        }
        this.state.isTested = false;
        this.model.unblock();
    }

    async handleImport(isTest = true) {
        const message = isTest ? _t("Testing") : _t("Importing");

        let blockComponent;
        if (this.isBatched) {
            blockComponent = {
                class: ImportDataProgress,
                props: {
                    stopImport: () => this.stopImport(),
                    totalSteps: this.totalSteps,
                    importProgress: this.state.importProgress,
                },
            };
        }

        this.model.block(message, blockComponent);

        let res = { ids: [] };
        try {
            const data = await this.model.executeImport(
                isTest,
                this.totalSteps,
                this.state.importProgress
            );
            res = data.res;
        } finally {
            this.model.unblock();
        }

        if (!isTest && res.nextrow) {
            this.state.isPaused = true;
        }

        if (res.ids.length) {
            if (!isTest) {
                if (res.hasError) {
                    return;
                }
                this.notification.add(_t("%s records successfully imported", res.ids.length), {
                    type: "success",
                });
                if (!this.state.isPaused) {
                    this.openRecords(res.ids);
                }
            } else {
                this.state.isTested = true;
            }
        }
    }

    stopImport() {
        this.model.stopImport();
    }

    //--------------------------------------------------------------------------
    // Fields
    //--------------------------------------------------------------------------

    onFieldChanged(column, fieldInfo) {
        this.model.setColumnField(column, fieldInfo);
    }

    isFieldSet(column) {
        return column.fieldInfo != null;
    }

    get hasBinaryFields() {
        return this.model.columns.some((column) => column.fieldInfo?.type === "binary");
    }
}

registry.category("actions").add("import", ImportAction);
