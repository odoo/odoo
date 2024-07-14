/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { Pager } from "@web/core/pager/pager";

import { KeepLast } from "@web/core/utils/concurrency";
import { SearchModel } from "@web/search/search_model";
import { useBus, useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { getDefaultConfig } from "@web/views/view";
import { _t } from "@web/core/l10n/translation";

import { Component, useState, useSubEnv, useChildSubEnv, onWillStart, useEffect } from "@odoo/owl";

export class TemplateDialog extends Component {
    setup() {
        this.orm = useService("orm");
        this.viewService = useService("view");
        this.notificationService = useService("notification");
        this.actionService = useService("action");
        this.companyService = useService("company");

        this.data = this.env.dialogData;
        useHotkey("escape", () => this.data.close());
        useHotkey("Enter", async () => {
            await this._createSpreadsheet();
        });

        this.dialogTitle = _t("Create a Spreadsheet or select a Template");
        this.limit = 9;
        this.state = useState({
            isOpen: true,
            templates: [],
            templatesCount: 0,
            selectedTemplateId: null,
            offset: 0,
            isCreating: false,
        });
        useSubEnv({
            config: {
                ...getDefaultConfig(),
            },
        });
        this.model = new SearchModel(this.env, {
            user: useService("user"),
            orm: this.orm,
            view: useService("view"),
        });
        useChildSubEnv({
            searchModel: this.model,
        });
        useBus(this.model, "update", () => this._fetchTemplates());
        this.keepLast = new KeepLast();

        onWillStart(async () => {
            const defaultFolder = await this.orm.searchRead(
                "res.company",
                [["id", "=", this.companyService.currentCompany.id]],
                ["documents_spreadsheet_folder_id"]
            );
            this.documentsSpreadsheetFolderId = defaultFolder[0].documents_spreadsheet_folder_id[0];
            const views = await this.viewService.loadViews({
                resModel: "spreadsheet.template",
                context: this.props.context,
                views: [[false, "search"]],
            });
            await this.model.load({
                resModel: "spreadsheet.template",
                context: this.props.context,
                orderBy: "id",
                searchMenuTypes: [],
                searchViewArch: views.views.search.arch,
                searchViewId: views.views.search.id,
                searchViewFields: views.fields,
            });
            await this._fetchTemplates();
        });

        useEffect(() => {
            this.state.offset = 0;
        }, () => [this.model.searchDomain]);
    }

    /**
     * Fetch templates according to the search domain and the pager
     * offset given as parameter.
     * @private
     * @param {number} offset
     * @returns {Promise<void>}
     */
    async _fetchTemplates(offset = 0) {
        const { domain, context } = this.model;
        const { records, length } = await this.keepLast.add(
            this.orm.webSearchRead("spreadsheet.template", domain, {
                specification: { name: {} },
                domain,
                context,
                offset,
                limit: this.limit,
                order: "sequence, id",
            })
        );
        this.state.templates = records;
        this.state.templatesCount = length;
    }

    /**
     * Will create a spreadsheet based on the currently selected template
     * and the current folder we are in. The user will be notified and
     * the newly created spreadsheet will be opened.
     * @private
     * @returns {Promise<void>}
     */
    async _createSpreadsheet() {
        if (!this._hasSelection()) {
            return;
        }
        this.state.isCreating = true;

        this.notificationService.add(_t("New sheet saved in Documents"), {
            type: "info",
            sticky: false,
        });

        this.actionService.doAction(await this._getOpenSpreadsheetAction(), {
            additionalContext: this.props.context,
        });
        this.data.close();
    }

    async _getOpenSpreadsheetAction() {
        const context = this.props.context;
        const templateId = this.state.selectedTemplateId;
        if (templateId) {
            return this.orm.call(
                "spreadsheet.template",
                "action_create_spreadsheet",
                [templateId, { folder_id: this.props.folderId || this.documentsSpreadsheetFolderId }],
                { context }
            );
        }
        return this.orm.call(
            "documents.document",
            "action_open_new_spreadsheet",
            [{ folder_id: this.props.folderId || this.documentsSpreadsheetFolderId }],
            { context }
        );
    }

    /**
     * Changes the currently selected template in the state.
     * @private
     * @param {number | null} templateId
     */
    _selectTemplate(templateId) {
        this.state.selectedTemplateId = templateId;
    }

    /**
     * Returns whether or not templateId is currently selected.
     * @private
     * @param {number | null} templateId
     * @returns {boolean}
     */
    _isSelected(templateId) {
        return this.state.selectedTemplateId === templateId;
    }

    /**
     * Check if any template or the Blank template is selected.
     * @private
     * @returns {boolean}
     */
    _hasSelection() {
        return (
            this.state.templates.find(
                (template) => template.id === this.state.selectedTemplateId
            ) || this.state.selectedTemplateId === null
        );
    }

    /**
     * This function will be called when the user uses the pager. Based on the
     * pager state, new templates will be fetched.
     * @private
     * @param {CustomEvent} ev
     * @returns {Promise<void>}
     */
    _onPagerChanged({ offset }) {
        this.state.offset = offset;
        return this._fetchTemplates(this.state.offset);
    }

    /**
     * Check if the create button should be disabled.
     * @private
     * @returns {boolean}
     */
    _buttonDisabled() {
        return this.state.isCreating || !this._hasSelection();
    }
}
TemplateDialog.components = { Dialog, SearchBar, Pager };
TemplateDialog.template = "documents_spreadsheet.TemplateDialog";
TemplateDialog.props = {
    context: Object,
    folderId: { type: Number, optional: true },
    close: Function, // prop added by the Dialog service
    folders: Array,
};
