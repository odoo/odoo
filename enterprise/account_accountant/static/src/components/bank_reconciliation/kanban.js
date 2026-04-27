/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { scrollTo } from "@web/core/utils/scrolling";
import { getCurrency } from "@web/core/currency";
import { formatMonetary } from "@web/views/fields/formatters";
import { formatDate } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";

import { CallbackRecorder, useSetupAction } from "@web/search/action_hook";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { makeActiveField } from "@web/model/relational_model/utils";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { DateTimeField } from "@web/views/fields/datetime/datetime_field";
import { CharField } from "@web/views/fields/char/char_field";
import { AnalyticDistribution } from "@analytic/components/analytic_distribution/analytic_distribution";
import { TagsList } from "@web/core/tags_list/tags_list";
import { HtmlField } from "@web_editor/js/backend/html_field";
import { RainbowMan } from "@web/core/effects/rainbow_man";
import { Notebook } from "@web/core/notebook/notebook";
import { user } from "@web/core/user";

import { BankRecRelationalModel } from "./bank_rec_record";
import { BankRecMonetaryField } from "./monetary_field_auto_signed_amount";
import { BankRecViewEmbedder } from "./view_embedder";
import { BankRecRainbowContent } from "./rainbowman_content";
import { BankRecFinishButtons } from "./finish_buttons";
import { BankRecGlobalInfo } from "./global_info";
import { BankRecQuickCreate } from "./bank_rec_quick_create";

import { onPatched, useState, useEffect, useRef, useChildSubEnv, markRaw } from "@odoo/owl";

export class BankRecKanbanRecord extends KanbanRecord {
    static template = "account.BankRecKanbanRecord";

    setup(){
        super.setup();
        this.state = useState(this.env.methods.getState());
    }

    /** @override **/
    getRecordClasses() {
        let classes = `${super.getRecordClasses()} w-100 o_bank_rec_st_line`;
        if (this.props.record.resId === this.state.bankRecStLineId) {
            classes = `${classes} o_bank_rec_selected_st_line table-info`;
        }
        return classes;
    }
}


export class BankRecKanbanController extends KanbanController {
    static template = "account.BankRecoKanbanController";
    static props = {
        ...KanbanController.props,
        skipRestore: { optional: true },
    };
    static components = {
        ...KanbanController.components,
        Dropdown,
        DropdownItem,
        Many2OneField,
        Many2ManyTagsField,
        DateTimeField,
        CharField,
        AnalyticDistribution,
        Chatter,
        TagsList,
        HtmlField,
        BankRecMonetaryField,
        Notebook,
        BankRecViewEmbedder,
    };

    async setup() {
        super.setup();

        // ==================== INITIAL SETUP ====================

        // Actions.
        this.action = useService("action");
        this.orm = useService("orm");
        this.ui = useService("ui");

        // RelationalModel services.
        this.relationalModelServices = Object.fromEntries(
            RelationalModel.services.map((servName) => {
                return [servName, useService(servName)];
            })
        );
        this.relationalModelServices.orm = useService("orm");

        useChildSubEnv(this.getChildSubEnv());

        // Mount the correct statement line when the search panel changed
        this.env.searchModel.addEventListener(
            "update",
            () => {
                this.model.bus.addEventListener(
                    "update",
                    this.onKanbanSearchModelChanged.bind(this),
                    { once: true },
                );
            },
        );

        // ==================== STATE ====================

        this.bankRecModel = null;

        this.state = useState({
            // BankRec.
            bankRecStLineId: null,
            bankRecRecordData: null,
            bankRecEmbeddedViewsData: null,
            bankRecNotebookPage: null,
            bankRecClickedColumn: null,

            // Global info.
            journalId: null,
            journalBalanceAmount: "",

            // Asynchronous validation stuff.
            lockedStLineIds: new Set(),
            lockedAmlIds: new Set(),

            quickCreateState : {
                isVisible: false,
                view: this.props.archInfo.quickCreateView,
                context: this.props.context,
            },
        });

        this.counter = {
            // Counter state is separated as it should not be impacted by asynchronous changes, the last update is final.
            startTime: null,
            timeDiff: null,
            count: null,
        };

        // When focusing the manual operations tab, mount the last line in edition automatically.
        useEffect(
            () => {
                if(
                    this.state.bankRecNotebookPage === "manual_operations_tab"
                    && this.state.bankRecRecordData
                    && !this.state.bankRecRecordData.form_index
                ){
                    this.actionMountLastLineInEdit();
                }
            },
            () => [this.state.bankRecNotebookPage],
        );

        // ==================== EXPORT STATE ====================

        this.viewRef = useRef("root");

        useSetupAction({
            rootRef: this.viewRef,
            getLocalState: () => {
                const exportState = {};
                if(this.bankRecModel.root.data.st_line_id){
                    exportState.backupValues = Object.assign(
                        {},
                        this.state.bankRecEmbeddedViewsData,
                        {
                            bankRecStLineId: this.state.bankRecStLineId,
                            initial_values: this.bankRecModel.getInitialValues(),
                        },
                    );
                }
                return exportState;
            }
        });

        onPatched(() => {
            if(
                this.state.bankRecClickedColumn
                && this.focusManualOperationField(this.state.bankRecClickedColumn)
            ){
                this.state.bankRecClickedColumn = null;
            }
        });

        // ==================== LOCK SCREEN ====================

        this.kanbanLock = false;
        this.bankRecLock = false;
        this.bankRecPromise = null;
    }

    // -----------------------------------------------------------------------------
    // HELPERS CONCURRENCY
    // -----------------------------------------------------------------------------

    /**
     * Execute the function passed as parameter initiated by the kanban.
     * If some action is already processing by bankRecForm, it will wait until its completion.
     * @param {Function} func: The action to execute.
     */
    async execProtectedAction(func){
        if(this.kanbanLock){
            return;
        }
        this.kanbanLock = true;
        if(this.bankRecPromise){
            await this.bankRecPromise;
        }
        await func();
        this.kanbanLock = false;
    }

    /**
     * Execute the function passed as parameter initiated by bankRecForm.
     * If some concurrent actions are triggered by bankRecForm, the second one is ignored.
     * @param {Function} func: The action to execute.
     */
    async execProtectedBankRecAction(func){
        if(this.bankRecLock){
            return;
        }
        this.bankRecLock = true;
        try {
            this.bankRecPromise = func();
            await this.bankRecPromise;
        } finally {
            this.bankRecPromise = null;
            this.bankRecLock = false;
        }
    }

    // -----------------------------------------------------------------------------
    // HELPERS STATE
    // -----------------------------------------------------------------------------

    getState(){
        return this.state;
    }

    /**
     * Since the kanban is driven by a reactive state for the additional stuff but by deep render
     * in its base implementation, the code is turning crazy with rendering everytime a deep render
     * is triggered. Indeed, notifying the model then changing things on the state could trigger a lot of
     * mount/unmount of components implying useless rpc requests (when mounting multiple times an
     * embedded list view for example).
     * To avoid that, this method must be used everywhere to update only once the state and to delay
     * the notify (itself triggering the deep render) after the update of the state.
     * @param {Function} func: The action to execute taking the newState as parameter.
     */
    async withNewState(func){
        const newState = {...this.state};
        await func(newState);
        if (newState.__commitChanges) {
            newState.__commitChanges();
            delete newState.__commitChanges;
        }
        Object.assign(this.state, newState);
    }

    // -----------------------------------------------------------------------------
    // KANBAN OVERRIDES
    // -----------------------------------------------------------------------------

    /** override **/
    get modelOptions() {
        return {
            ...super.modelOptions,
            onWillStartAfterLoad: this.onWillStartAfterLoad.bind(this),
        }
    }

    /**
     * Define the sub environment allowing the sub-components to access some methods from
     * the kanban.
     */
    getChildSubEnv(){
        return {
            // We don't care about subview states but we want to avoid them to record
            // some callbacks in the BankRecKanbanController callback recorders passed
            // by the action service.
            __beforeLeave__: new CallbackRecorder(),
            __getLocalState__: new CallbackRecorder(),
            __getGlobalState__: new CallbackRecorder(),
            __getContext__: new CallbackRecorder(),

            // Accessible methods from sub-components.
            methods: {
                withNewState: this.withNewState.bind(this),
                actionOpenBankGL: this.actionOpenBankGL.bind(this),
                focusManualOperationField: this.focusManualOperationField.bind(this),
                getState: this.getState.bind(this),
                actionAddNewAml: this.actionAddNewAml.bind(this),
                actionRemoveNewAml: this.actionRemoveNewAml.bind(this),
                showRainbowMan: this.showRainbowMan.bind(this),
                initReconCounter: this.initReconCounter.bind(this),
                getCounterSummary: this.getCounterSummary.bind(this),
                getRainbowManContentProps: this.getRainbowManContentProps.bind(this),
                updateJournalState: this.updateJournalState.bind(this),
            },
        };
    }

    /** Called when the kanban is initialized. **/
    async onWillStartAfterLoad(){
        // Fetch groups.
        this.hasGroupAnalyticAccounting = await user.hasGroup("analytic.group_analytic_accounting");
        this.hasGroupReadOnly = await user.hasGroup("account.group_account_readonly");


        // Prepare bankRecoModel.
        await this.initBankRecModel();

        let stLineId = null;
        let backupValues = null;

        // Try to restore.
        if(this.props.state && this.props.state.backupValues && !this.props.skipRestore){
            const backupStLineId = this.props.state.backupValues.bankRecStLineId;
            if(this.model.root.records.find(x => x.resId === backupStLineId)){
                stLineId = backupStLineId;
                backupValues = this.props.state.backupValues;
            }
        }

        // Find the next transaction to mount.
        if(!stLineId){
            stLineId = this.getNextAvailableStLineId();
        }

        await this.withNewState(async (newState) => {

            // Mount the transaction if any.
            if(stLineId){
                await this._mountStLineInEdit(newState, stLineId, backupValues);
            }else{
                await this.updateJournalState(newState);
            }

            this.initReconCounter();
        });
    }

    /** Called when the something changed in the kanban search model. **/
    async onKanbanSearchModelChanged(){
        await this.execProtectedAction(async () => {
            await this.withNewState(async (newState) => {
                if(this.model.root.records.find(x => x.resId === newState.bankRecStLineId)){
                    return;
                }

                const nextStLineId = this.getNextAvailableStLineId();
                await this._mountStLineInEdit(newState, nextStLineId);
            });
        });
    }

    /**
    Method called when the user clicks on a card.
    **/
    async openRecord(record, mode) {
        const currentStLineId = this.bankRecModel ? this.bankRecModel.root.data.st_line_id[0] : null;
        const isSameStLineId = currentStLineId && currentStLineId === record.resId;
        if (isSameStLineId) {
            return;
        }
        await this.execProtectedAction(async () => {
            await this.withNewState(async (newState) => {
                await this._mountStLineInEdit(newState, record.resId);
            });
        });
    }

    /**
    Method called when the user changes the search pager.
    **/
    async onUpdatedPager() {
        await this.execProtectedAction(async () => {
            await this.withNewState(async (newState) => {
                const nextStLineId = this.getNextAvailableStLineId();
                await this._mountStLineInEdit(newState, nextStLineId);
            });
        });
    }

    onPageUpdate(page) {
        if (this.state.bankRecNotebookPage !== page) {
            this.state.bankRecNotebookPage = page;
        }
    }

    /**
    Overriden.
    **/
    get canQuickCreate() {
        return true;
    }

    /**
    Overriden.
    **/
    createRecord() {
        const { onCreate } = this.props.archInfo;
        const searchModel = this.env.searchModel;
        const journalFilter = Object.values(searchModel.searchItems).filter(i => i.type == "field" && i.fieldName == "journal_id")[0];

        // If there are no records, deactivate all filters except the journal one.
        if (!this.model.root.records.length) {
            searchModel.facets.forEach(facet => {
                if(facet.groupId !== journalFilter.groupId)
                    searchModel.deactivateGroup(facet.groupId)
            });
        }

        if (onCreate === "quick_create" && this.canQuickCreate) {
            this.state.quickCreateState = {
                ...this.state.quickCreateState,
                isVisible: true,
                resModel: this.props.resModel,
                model: this.model,
            };
        }
    }

    // -----------------------------------------------------------------------------
    // NEXT STATEMENT LINE
    // -----------------------------------------------------------------------------

    /**
    Get the next eligible statement line for reconciliation.
    @param afterStLineId:   An optional id of a statement line indicating we want the
                            next available line after this one.
    @param records:         An optional list of records.
    **/
    getNextAvailableStLineId(afterStLineId=null, records=null) {
        const stLines = this.model.root.records;

        // Find all available records that need to be validated.
        const isRecordReady = (x) => (!x.data.is_reconciled || !x.data.checked);
        let waitBeforeReturn = Boolean(afterStLineId);
        let availableRecordIds = [];
        for (const stLine of (records || stLines)) {
            if (waitBeforeReturn) {
                if (stLine.resId === afterStLineId) {
                    waitBeforeReturn = false;
                }
            } else if (isRecordReady(stLine)) {
                availableRecordIds.push(stLine.resId);
            }
        }

        // No records left, focus the first record instead. This behavior is mainly there when clicking on "View" from
        // the list view to show an already reconciled line.
        if (!availableRecordIds.length && stLines.length === 1) {
            availableRecordIds = [stLines[0].resId];
        }

        if (availableRecordIds.length){
            return availableRecordIds[0];
        } else if(stLines.length) {
            return stLines[0].resId;
        } else {
            return null;
        }
    }

    /**
    Mount the statement line passed as parameter into the edition widget.
    @param stLineId: The id of the statement line to mount.
    **/
    async _mountStLineInEdit(newState, stLineId, initialData = null) {
        newState.bankRecStLineId = stLineId;
        let data = {};
        if (initialData) {
            // Restore an existing transaction.
            data = await this.onchange(newState, "restore_st_line_data", [initialData]);
            const bankRecEmbeddedViewsData = data.return_todo_command;
            for (const [key, value] of Object.entries(bankRecEmbeddedViewsData)) {
                if (value instanceof Object) {
                    bankRecEmbeddedViewsData[key] = Object.assign(
                        {},
                        initialData[key] || {},
                        value
                    );
                } else {
                    bankRecEmbeddedViewsData[key] = value;
                }
            }
            newState.bankRecEmbeddedViewsData = markRaw(bankRecEmbeddedViewsData);
            newState.bankRecNotebookPage = null;
        } else if (stLineId) {
            // Mount a new transaction.
            data = await this.onchange(newState, "mount_st_line", [stLineId]);
            const bankRecEmbeddedViewsData = data.return_todo_command
            newState.bankRecEmbeddedViewsData = bankRecEmbeddedViewsData;
            newState.bankRecNotebookPage = null;
        } else {
            // No transaction mounted.
            newState.bankRecNotebookPage = null;
            newState.bankRecRecordData = null;
        }

        // Refresh balance.
        await this.updateJournalState(newState, data);

        // Scroll to the next kanban card iff the view is mounted, a line is selected  and the kanban
        // card is in the view (cannot use .o_bank_rec_selected_st_line as the dom may not be patched yet)
        if (stLineId && this.viewRef.el) {
            const selectedKanbanCardEl = this.viewRef.el.querySelector(
                `[st-line-id="${stLineId}"]`
            );
            if (selectedKanbanCardEl) {
                scrollTo(selectedKanbanCardEl, {});
            }
        }
    }

    /**
    Mount the statement line passed as parameter into the edition widget.
    @param stLineId: The id of the statement line to mount.
    **/
    async mountStLineInEdit(stLineId, initialData=null){
        await this.withNewState(async (newState) => {
            await this._mountStLineInEdit(newState, stLineId, initialData);
        });
    }

    // -----------------------------------------------------------------------------
    // BANK_REC_RECORD
    // -----------------------------------------------------------------------------

    async initBankRecModel(){
        const initialData = await this.orm.call(
            "bank.rec.widget",
            "fetch_initial_data",
        );

        // Services.
        function makeActiveFields(fields) {
            const activeFields = {};
            for (const fieldName in fields) {
                const field = fields[fieldName];
                activeFields[fieldName] = makeActiveField({ onChange: field.onChange});
                if (field.relatedFields) {
                    activeFields[fieldName].related = {
                        fields: field.relatedFields,
                        activeFields: makeActiveFields(field.relatedFields),
                    }
                }
            }
            return activeFields;
        }
        const activeFields = makeActiveFields(initialData.fields);
        this.bankRecModel = new BankRecRelationalModel(
            this.env,
            {
                config: {
                    resModel: "bank.rec.widget",
                    fields: initialData.fields,
                    activeFields,
                    mode: "edit",
                    isMonoRecord: true,
                }
            },
            this.relationalModelServices,
        );

        // Initial loading.
        await this.bankRecModel.load({
            values: initialData.initial_values,
        });

        const record = this.bankRecModel.root;
        record.bindActionOnLineChanged(async (changedField) => {
            await this.actionLineChanged(changedField);
        });
    }

    getBankRecRecordLineInEdit(){
        const data = this.state.bankRecRecordData;
        const lineIndex = data.form_index;
        return data.line_ids.records.find((x) => x.data.index === lineIndex);
    }

    // -----------------------------------------------------------------------------
    // GLOBAL INFO
    // -----------------------------------------------------------------------------

    async updateJournalState(newState, data = {}) {
        // Find the journal.
        let journalId = null;
        const stLineJournalId = data.st_line_journal_id;
        if(stLineJournalId){
            journalId = stLineJournalId[0];
        }else if(this.model.root.records.length){
            journalId = this.model.root.records[0].data.journal_id[0];
        }else{
            journalId = this.props.context.default_journal_id;
        }
        newState.journalId = journalId;
        const values = await this.orm.call(
            "bank.rec.widget",
            "collect_global_info_data",
            [journalId],
        );
        newState.journalBalanceAmount = values.balance_amount;
    }

    // -----------------------------------------------------------------------------
    // COUNTER / RAINBOWMAN
    // -----------------------------------------------------------------------------

    /** Reset the timing and reconciliation counter */
    initReconCounter() {
        this.counter.startTime = luxon.DateTime.now();
        this.counter.timeDiff = null;
        this.counter.count = 0;
    }

    /** Increment the timing and reconciliation counter */
    incrementReconCounter() {
        const start = this.counter.startTime.set({millisecond: 0});
        const end = luxon.DateTime.now().set({millisecond: 0});
        this.counter.timeDiff = end.diff(start, "seconds");
        this.counter.count += 1;
    }

    showRainbowMan(){
        return this.counter.count > 0;
    }

    getCounterSummary() {
        const diff = this.counter.timeDiff;
        const total = this.counter.count;
        const diffInSeconds = diff.seconds;
        let units = ["seconds"];
        if (diffInSeconds > 60) {
            units.unshift("minutes");
        }
        if (diffInSeconds > 3600) {
            units.unshift("hours");
        }
        return {
            counter: total,
            secondsPerTransaction: Math.round(diffInSeconds / total),
            formattedDuration: diff.toFormat(localization.timeFormat.replace(/HH/, "hh")),
            humanDuration: diff.shiftTo(...units).toHuman(),
        }
    }

    getRainbowManContentProps(){
        return {
            fadeout: "no",
            message: "",
            imgUrl: "/web/static/img/smile.svg",
            Component: BankRecRainbowContent,
            close: () => {},
        }
    }

    // -----------------------------------------------------------------------------
    // HELPERS BANK_REC_RECORD
    // -----------------------------------------------------------------------------

    async moveToNextLine(newState){
        const records = this.model.root.records;
        const counter = newState.counter;
        await this.model.root.load();

        const nextStLineId = this.getNextAvailableStLineId(newState.bankRecStLineId, records);
        if(nextStLineId != newState.bankRecStLineId){
            await this._mountStLineInEdit(newState, nextStLineId);
        }
        newState.counter = counter;
        newState.__kanbanNotify = true;
    }

    formatMonetaryField(amount, currencyId){
        const currencyDigits = getCurrency(currencyId)?.digits;
        return formatMonetary(amount, {
            digits: currencyDigits,
            currencyId: currencyId,
        });
    }

    isMonetaryZero(amount, currencyId){
        const currencyDigits = getCurrency(currencyId)?.digits;
        return Number(amount.toFixed(currencyDigits ? currencyDigits[1] : 2)) === 0;
    }

    formatDateField(date){
        return formatDate(date);
    }

    async onchange(newState, methodName, args, kwargs){
        const record = this.bankRecModel.root;
        const { data, applyChanges } = await record.updateToDoCommand(methodName, args, kwargs);

        newState.__commitChanges = () => {
            applyChanges();
            newState.bankRecRecordData = record.data;
            newState.__bankRecRecordNotify = true;
        };
        return data;
    }

    getOne2ManyColumns() {
        const data = this.state.bankRecRecordData;
        let lineIdsRecords = data.line_ids.records;

        // Prepare columns.
        let columns = [
            ["date", _t("Date")],
            ["partner", _t("Partner")],
        ];
        if(lineIdsRecords.some((x) => Boolean(Object.keys(x.data.analytic_distribution).length))){
            columns.push(["analytic_distribution", _t("Analytic")]);
        }
        if(lineIdsRecords.some((x) => x.data.tax_ids.records.length)){
            columns.push(["taxes", _t("Taxes")]);
        }
        if(lineIdsRecords.some((x) => x.data.currency_id[0] !== data.company_currency_id[0])){
            columns.push(["amount_currency", _t("Amount in Currency")], ["currency", _t("Currency")]);
        }
        if (this.hasGroupReadOnly) {
            columns.unshift(["account", _t("Account")]);
            columns.push(
                ["debit", _t("Debit")],
                ["credit", _t("Credit")],
                ["__trash", ""],
            );
        } else {
            columns.push(
                ["balance", _t("Amount")],
                ["__trash", ""],
            );
        }

        return columns;
    }

    getKey(lineData) {
        return `${lineData.index} ${JSON.stringify(lineData.analytic_distribution)}`;
    }

    checkBankRecLineRequiredField(line, invalidFields, fieldName, condition){
        if(!line.data[fieldName] && (!condition || condition())){
            invalidFields.push(fieldName);
        }
    }

    getBankRecLineInvalidFields(line){
        const invalidFields = [];
        this.checkBankRecLineRequiredField(line, invalidFields, "account_id");
        this.checkBankRecLineRequiredField(line, invalidFields, "date", () => line.data.flag === "liquidity");
        return invalidFields;
    }

    checkBankRecLinesInvalidFields(data){
        return data.line_ids.records.filter((l) => this.getBankRecLineInvalidFields(l).length > 0).length === 0;
    }

    notebookAmlsListViewProps(){
        const initParams = this.state.bankRecEmbeddedViewsData.amls;
        const ctx = initParams.context;
        const suspenseLine = this.state.bankRecRecordData.line_ids.records.filter((l) => l.data.flag == "auto_balance");
        if (suspenseLine.length) {
            // Change the sort order of the AML's in the list view based on the amount of the suspense line
            // This is done from JS instead of python because the embedded_views_data is only prepared when selecting
            // a statement line, and not after mounting an AML that would change the auto_balance value (suspense line)
            ctx['preferred_aml_value'] = suspenseLine[0].data.amount_currency * -1;
            ctx['preferred_aml_currency_id'] = suspenseLine[0].data.currency_id[0];
        }
        return {
            type: "list",
            noBreadcrumbs: true,
            resModel: "account.move.line",
            searchMenuTypes: ["filter", "favorite"],
            domain: initParams.domain,
            dynamicFilters: initParams.dynamic_filters,
            context: ctx,
            allowSelectors: false,
            searchViewId: false, // little hack: force to load the search view info
            globalState: initParams.exportState,
            loadIrFilters: true,
        }
    }

    /**
    Focus the field corresponding to the column name passed as parameter inside the
    manual operation page.
    **/
    focusManualOperationField(clickedColumn){
        // Focus the field corresponding to the clicked column.
        if (['debit', 'credit'].includes(clickedColumn)) {
            if (this.focusElement("div[name='balance'] input")) {
                return true;
            }
            if (this.focusElement("div[name='amount_currency'] input")) {
                return true;
            }
        }

        if (this.focusElement(`div[name='${clickedColumn}'] input`)) {
            return true;
        }
        if (this.focusElement(`input[name='${clickedColumn}']`)) {
            return true;
        }
        return false;
    }

    /** Helper to find the corresponding field to focus inside the DOM. **/
    focusElement(selector) {
        const inputEl = this.viewRef.el.querySelector(selector);
        if (!inputEl) {
            return false;
        }

        if (inputEl.tagName === "INPUT") {
            inputEl.focus();
            inputEl.select();
        } else {
            inputEl.focus();
        }
        return true;
    }

    // -----------------------------------------------------------------------------
    // RPC
    // -----------------------------------------------------------------------------

    async actionOpenBankGL(journalId) {
        const actionData = await this.orm.call(
            "account.journal",
            "action_open_bank_balance_in_gl",
            [journalId],
        );
        this.action.doAction(actionData);
    }

    async actionRemoveLine(line){
        await this.execProtectedBankRecAction(async () => {
            await this.withNewState(async (newState) => {
                await this.onchange(newState, "remove_line", [line.data.index]);

                if(newState.bankRecNotebookPage === "manual_operations_tab"){
                    newState.bankRecNotebookPage = "amls_tab";
                }
            });
        });
    }

    async actionSelectRecoModel(recoModel){
        await this.execProtectedBankRecAction(async () => {
            await this.withNewState(async (newState) => {
                const data = newState.bankRecRecordData;
                if(recoModel.resId == data.selected_reco_model_id.id){
                    return;
                }
                const { return_todo_command: actionData } = await this.onchange(newState, "select_reconcile_model", [recoModel.resId])
                if(actionData){
                    this.action.doAction(actionData);
                }
            });
        });
    }

    actionCreateRecoModel(){
        this.execProtectedBankRecAction(async () => {
            const journalId = this.state.bankRecRecordData.st_line_journal_id[0];
            const lines = this.state.bankRecRecordData.line_ids.records;

            const defaultLineIds = [];
            let balance = lines.filter(line => line.data.flag === "liquidity")[0].data.balance
            if(!this.isMonetaryZero(balance, this.state.bankRecRecordData.company_currency_id[0])){
                for (const line of lines) {
                    const data = line.data;
                    if (!["manual", "aml"].includes(data.flag)){
                        continue;
                    }

                    defaultLineIds.push([0, 0, {
                        label: data.name,
                        account_id: data.account_id[0],
                        tax_ids: [[6, 0, data.tax_ids.currentIds]],
                        amount_type: "percentage",
                        amount_string: ((-data.balance / balance) * 100).toFixed(5),
                    }]);
                    balance += data.balance;
                }
            }

            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "account.reconcile.model",
                views: [[false, "form"]],
                target: "current",
                context: {
                    default_match_journal_ids: [journalId],
                    default_line_ids: defaultLineIds,
                    default_to_check: !this.state.bankRecRecordData.checked,
                },
            });
        });
    }

    actionViewRecoModels(){
        this.execProtectedBankRecAction(async () => {
            this.action.doAction("account.action_account_reconcile_model");
        });
    }

    async _actionValidate(newState){
        const { return_todo_command: result } = await this.onchange(newState, "validate");
        if(result.done){
            this.incrementReconCounter();
            await this.moveToNextLine(newState);
        }
        return result;
    }

    async actionValidate(){
        await this.execProtectedBankRecAction(async () => {
            await this.withNewState(async (newState) => {
                await this._actionValidate(newState);
            });
        });
    }

    async actionReset(){
        await this.execProtectedBankRecAction(async () => {
            await this.withNewState(async (newState) => {
                const { return_todo_command: result } = await this.onchange(newState, "reset");

                if(result.done){
                    await this.model.root.load();

                    const stLineId = newState.bankRecStLineId;
                    if(!stLineId){
                        return;
                    }

                    const records = this.model.root.records;
                    if(!records.length){
                        // The transaction is not longer available on the kanban.
                        newState.bankRecStLineId = null;
                        newState.bankRecNotebookPage = null;
                        newState.bankRecRecordData = null;
                    }else if(!records.find((x) => x.resId === stLineId)){
                        // Move to the next available transaction.
                        const nextStLineId = this.getNextAvailableStLineId(stLineId);
                        await this._mountStLineInEdit(newState, nextStLineId);
                    }

                    if(newState.bankRecNotebookPage != "amls_tab"){
                        newState.bankRecNotebookPage = "amls_tab";
                    }

                    newState.__kanbanNotify = true;
                }
            });
        });
    }

    async actionToCheck(){
        await this.execProtectedBankRecAction(async () => {
            await this.withNewState(async (newState) => {
                const { return_todo_command: result } = await this.onchange(newState, "to_check");
                if(result.done){
                    await this.moveToNextLine(newState);
                }
            });
        });
    }

    async actionSetAsChecked(){
        await this.execProtectedBankRecAction(async () => {
            await this.withNewState(async (newState) => {
                const data = await this.onchange(newState, "set_as_checked");
                const result = data.return_todo_command;
                if(result.done && data.state === "reconciled"){
                    await this.moveToNextLine(newState);
                }else{
                    await this.model.root.load();
                    newState.__kanbanNotify = true;
                }
            });
        });
    }

    async actionAddNewAml(amlId){
        await this.execProtectedBankRecAction(async () => {
            await this.withNewState(async (newState) => {
                await this.onchange(newState, "add_new_aml", [amlId]);
            });
        });
    }

    async actionRemoveNewAml(amlId){
        await this.execProtectedBankRecAction(async () => {
            await this.withNewState(async (newState) => {
                await this.onchange(newState, "remove_new_aml", [amlId]);
             });
        });
    }

    async _actionMountLineInEdit(newState, line){
        const data = newState.bankRecRecordData;
        const currentLineIndex = data.form_index;
        if(line.data.index != currentLineIndex){
            // Mount the line in edition on the form.
            await this.onchange(newState, "mount_line_in_edit", [line.data.index]);
        }

        if(newState.bankRecNotebookPage !== "manual_operations_tab"){
            newState.bankRecNotebookPage = "manual_operations_tab";
        }
    }

    async actionMountLineInEdit(line){
        await this.execProtectedBankRecAction(async () => {
            await this.withNewState(async (newState) => {
                await this._actionMountLineInEdit(newState, line);
            });
        });
    }

    async actionMountLastLineInEdit(){
        await this.execProtectedBankRecAction(async () => {
            await this.withNewState(async (newState) => {
                const data = newState.bankRecRecordData;
                const line = data.line_ids.records.at(-1);
                await this._actionMountLineInEdit(newState, line);
            });
        });
    }

    async postprocessLineChangedReturnTodoCommand(newState, data) {
        const todo = data.return_todo_command;
        if(!todo){
            return;
        }
        if(todo.reset_record){
            await this.model.root.load();
            newState.__kanbanNotify = true;
        }
        if(todo.reset_global_info){
            await this.updateJournalState(newState, data);
        }
    }

    async actionLineChanged(fieldName){
        await this.execProtectedBankRecAction(async () => {
            const line = this.getBankRecRecordLineInEdit();
            await this.withNewState(async (newState) => {
                if(line){
                    const data = await this.onchange(newState, "line_changed", [line.data.index, fieldName]);
                    await this.postprocessLineChangedReturnTodoCommand(newState, data);
                }
            });
        });
    }

    async actionSetPartnerReceivableAccount(){
        await this.execProtectedBankRecAction(async () => {
            const line = this.getBankRecRecordLineInEdit();
            await this.withNewState(async (newState) => {
                if(line){
                    const data = await this.onchange(newState, "line_set_partner_receivable_account", [line.data.index])
                    await this.postprocessLineChangedReturnTodoCommand(newState, data);
                }
            });
        });
    }

    async actionSetPartnerPayableAccount(){
        await this.execProtectedBankRecAction(async () => {
            const line = this.getBankRecRecordLineInEdit();
            await this.withNewState(async (newState) => {
                if(line){
                    const data = await this.onchange(newState, "line_set_partner_payable_account", [line.data.index])
                    await this.postprocessLineChangedReturnTodoCommand(newState, data);
                }
            });
        });
    }

    async actionRedirectToSourceMove(line){
        await this.execProtectedBankRecAction(async () => {
            await this.withNewState(async (newState) => {
                const { return_todo_command: actionData } = await this.onchange(newState, "redirect_to_move", [line.data.index])
                if(actionData){
                    this.action.doAction(actionData);
                }
            });
        });
    }

    async actionApplyLineSuggestion(){
        await this.execProtectedBankRecAction(async () => {
            const line = this.getBankRecRecordLineInEdit();
            await this.withNewState(async (newState) => {
                if(line){
                    await this.onchange(newState, "apply_line_suggestion", [line.data.index])
                }
            });
        });
    }

    async handleLineClicked(ev, line){
        const lineIndexBeforeClick = this.state.bankRecRecordData.form_index;
        await this.actionMountLineInEdit(line);

        let clickedColumn = null;
        const target = ev.target.tagName === "TD" ? ev.target : ev.target.closest("td");
        if (target?.attributes && target.attributes.field) {
            clickedColumn = target.attributes.field.value;
        }

        // Track the clicked column to focus automatically the corresponding field on the manual operations page.
        // In case we did not change the selected line we directly focus the corresponding field.
        if(clickedColumn){
            if(lineIndexBeforeClick === line.data.index) {
                this.focusManualOperationField(clickedColumn);
                this.state.bankRecClickedColumn = null;
            } else {
                this.state.bankRecClickedColumn = clickedColumn;
            }
        }
    }

    async handleSuggestionHtmlClicked(ev){
        if (ev.target.tagName === "BUTTON"){
            const buttonName = ev.target.attributes && ev.target.attributes.name ? ev.target.attributes.name.value : null;
            if (!buttonName) {
                return;
            }

            if (buttonName === "action_redirect_to_move"){
                const line = this.getBankRecRecordLineInEdit();
                await this.actionRedirectToSourceMove(line);
            } else if (buttonName === "action_apply_line_suggestion"){
                await this.actionApplyLineSuggestion();
            }
        }
    }

}

export class BankRecKanbanRenderer extends KanbanRenderer {
    static template = "account.BankRecKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: BankRecKanbanRecord,
        RainbowMan,
        BankRecFinishButtons,
        BankRecGlobalInfo,
        BankRecQuickCreate,
    };
    setup() {
        super.setup();
        this.globalState = useState(this.env.methods.getState());
        this.action = useService("action");
    }

    /**
    Prepares a list of statements based on the statement_id of the bank statement line records.
    Statements are only displayed above the first line of the statement (all lines might not be visible in the kanban)
    **/
    groups() {
        const { list } = this.props;
        let statementGroups = [];
        for (const record of list.records) {
            let lastItem = statementGroups.slice(-1);
            let statementId = record.data.statement_id && record.data.statement_id[0];
            if (statementId && (!lastItem.length || lastItem[0].id != statementId)) {
                statementGroups.push({
                    id: statementId,
                    name: record.data.statement_name,
                    balance: formatMonetary(record.data.statement_balance_end_real, {currencyId: record.data.currency_id[0]}),
                });
            }
        }
        return statementGroups;
    }

    openStatementDialog(statementId) {
        const action = {
            type: "ir.actions.act_window",
            res_model: "account.bank.statement",
            res_id: statementId,
            views: [[false, "form"]],
            target: "current",
            context: {
                form_view_ref: "account_accountant.view_bank_statement_form_bank_rec_widget",
            },
        };

        this.action.doAction(action);
    }

    // -----------------------------------------------------------------------------
    // QUICK CREATE CALLBACKS
    // -----------------------------------------------------------------------------

    /**
    Overriden.
    **/
    cancelQuickCreate() {
        this.globalState.quickCreateState.isVisible = false;
    }

    /**
    Overriden.
    **/
    validateQuickCreate(_recordId, mode) {
        this.globalState.quickCreateState.model.load()
        if (mode === "add_close") {
            this.globalState.quickCreateState.isVisible = false;
        }
    }
}

export const BankRecKanbanView = {
    ...kanbanView,
    Controller: BankRecKanbanController,
    Renderer: BankRecKanbanRenderer,
    searchMenuTypes: ["filter", "favorite"],
};

registry.category("views").add('bank_rec_widget_kanban', BankRecKanbanView);
