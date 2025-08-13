import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { makeContext } from "@web/core/context";
import { Dialog } from "@web/core/dialog/dialog";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { RPCError } from "@web/core/network/rpc";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import {
    useBus,
    useChildRef,
    useForwardRefToParent,
    useOwnedDialogs,
    useService,
} from "@web/core/utils/hooks";
import { createElement, parseXML } from "@web/core/utils/xml";
import { extractFieldsFromArchInfo, useRecordObserver } from "@web/model/relational_model/utils";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { loadSubViews, useFormViewInDialog } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { computeViewClassName, isNull } from "@web/views/utils";
import { ViewButton } from "@web/views/view_button/view_button";
import { executeButtonCallback, useViewButtons } from "@web/views/view_button/view_button_hook";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

/**
 * @typedef {Object} RelationalActiveActions {
 * @property {"x2m"} type
 * @property {boolean} create
 * @property {boolean} createEdit
 * @property {boolean} delete
 * @property {boolean} [link]
 * @property {boolean} [unlink]
 * @property {boolean} [write]
 * @property {Function | null} onDelete
 *
 * @typedef {import("services").Services} Services
 */

import {
    Component,
    onWillUpdateProps,
    status,
    useComponent,
    useEffect,
    useEnv,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";
import { highlightText, odoomark } from "@web/core/utils/html";

//
// Commons
//
export function useSelectCreate({ resModel, activeActions, onSelected, onCreateEdit, onUnselect }) {
    const addDialog = useOwnedDialogs();

    function selectCreate({ domain, context, filters, title }) {
        addDialog(SelectCreateDialog, {
            title: title || _t("Select records"),
            noCreate: !activeActions.create,
            multiSelect: "link" in activeActions ? activeActions.link : false, // LPE Fixme
            resModel,
            context,
            domain,
            onSelected,
            onCreateEdit: () => onCreateEdit({ context }),
            dynamicFilters: filters,
            onUnselect,
        });
    }
    return selectCreate;
}

const STANDARD_ACTIVE_ACTIONS = ["create", "createEdit", "delete", "link", "unlink", "write"];

/**
 * FIXME: this should somehow be merged with 'getActiveActions' (@web/views/utils.js)
 * Also I don't think storing a function in a collection of booleans is a good idea...
 *
 * @param {Object} params
 * @param {string} params.fieldType
 * @param {Record<string, boolean>} [params.subViewActiveActions={}]
 * @param {Object} [params.crudOptions={}]
 * @param {(props: Record<string, any>) => Record<any, any>} [params.getEvalParams=() => ({})]
 * @returns {RelationalActiveActions}
 */
export function useActiveActions({
    fieldType,
    subViewActiveActions = {},
    crudOptions = {},
    getEvalParams = () => ({}),
}) {
    const compute = ({ evalContext = {}, readonly = true }) => {
        /** @type {RelationalActiveActions} */
        const result = { type: fieldType, onDelete: null };
        const evalAction = (actionName) => evals[actionName](evalContext);

        // We need to take care of tags "control" and "create" to set create stuff
        result.create = !readonly && evalAction("create");
        result.createEdit = !readonly && result.create && crudOptions.createEdit; // always a boolean
        result.edit = crudOptions.edit;
        result.delete = !readonly && evalAction("delete");

        if (isMany2Many) {
            result.link = !readonly && evalAction("link");
            result.unlink = !readonly && evalAction("unlink");
            result.write = evalAction("write");
        }

        if (result.unlink || (!isMany2Many && result.delete)) {
            result.onDelete = crudOptions.onDelete;
        }

        return result;
    };

    const props = useComponent().props;
    const isMany2Many = fieldType === "many2many";

    // Define eval functions
    const evals = {};
    for (const actionName of STANDARD_ACTIVE_ACTIONS) {
        let evalFn = () => actionName !== "write";
        if (!isNull(crudOptions[actionName])) {
            const action = crudOptions[actionName];
            evalFn = (evalContext) => Boolean(action && new Domain(action).contains(evalContext));
        }

        if (actionName in subViewActiveActions) {
            const viewActiveAction = subViewActiveActions[actionName];
            evals[actionName] = (evalContext) => viewActiveAction && evalFn(evalContext);
        } else {
            evals[actionName] = evalFn;
        }
    }

    // Compute active actions
    const activeActions = compute(getEvalParams(props));
    onWillUpdateProps((nextProps) => {
        Object.assign(activeActions, compute(getEvalParams(nextProps)));
    });

    return activeActions;
}

/**
 * @template T, [Props=any], [Env=any]
 * @param {(orm: Services["orm"], props: Component<Props, Env>["props"]) => Promise<T>} loadFn
 */
export function useSpecialData(loadFn) {
    const component = useComponent();
    const record = component.props.record;
    const { specialDataCaches } = record.model;
    const orm = component.env.services.orm;
    const ormWithCache = Object.create(orm);
    ormWithCache.call = async (...args) => {
        const key = JSON.stringify(args);
        if (!specialDataCaches[key]) {
            return await orm
                .cache({
                    type: "disk",
                    update: "always",
                    callback: (res, hasChanged) => {
                        specialDataCaches[key] = Promise.resolve(res);
                        if (status(component) !== "destroyed" && hasChanged) {
                            loadFn(ormWithCache, component.props).then((res) => {
                                result.data = res;
                            });
                        }
                    },
                })
                .call(...args);
        }
        return specialDataCaches[key];
    };

    /** @type {{ data: Record<string, T> }} */
    const result = useState({ data: {} });
    useRecordObserver(async (record, props) => {
        result.data = await loadFn(ormWithCache, { ...props, record });
    });
    onWillUpdateProps(async (props) => {
        // useRecordObserver callback is not called when the record doesn't change
        if (props.record.id === component.props.record.id) {
            result.data = await loadFn(ormWithCache, props);
        }
    });
    return result;
}

//
// Many2X
//

export class Many2XAutocomplete extends Component {
    static template = "web.Many2XAutocomplete";
    static components = { AutoComplete };
    static props = {
        activeActions: Object,
        autoSelect: { type: Boolean, optional: true },
        autocomplete_container: { type: Function, optional: true },
        autofocus: { type: Boolean, optional: true },
        context: { type: Object, optional: true },
        createAction: { type: Function, optional: true },
        dropdown: { type: Boolean, optional: true },
        fieldString: String,
        getDomain: Function,
        id: { type: String, optional: true },
        isToMany: { type: Boolean, optional: true },
        nameCreateField: { type: String, optional: true },
        otherSources: { type: Array, optional: true },
        placeholder: { type: String, optional: true },
        quickCreate: { type: [Function, { value: null }], optional: true },
        resModel: String,
        searchLimit: { type: Number, optional: true },
        searchMoreLabel: { type: String, optional: true },
        searchMoreLimit: { type: Number, optional: true },
        searchThreshold: { type: Number, optional: true },
        setInputFloats: { type: Function, optional: true },
        slots: { optional: true },
        specification: { type: Object, optional: true },
        update: Function,
        value: { type: String, optional: true },
    };
    static defaultProps = {
        context: {},
        dropdown: true,
        nameCreateField: "name",
        otherSources: [],
        quickCreate: null,
        searchLimit: 7,
        searchThreshold: 0,
        searchMoreLimit: 320,
        setInputFloats: () => {},
        specification: {},
        value: "",
    };
    setup() {
        this.orm = useService("orm");

        this.autoCompleteContainer = useForwardRefToParent("autocomplete_container");
        const { activeActions, resModel, update, isToMany, fieldString } = this.props;

        this.keepLast = new KeepLast();

        this.openMany2X =
            this.props.createAction ??
            useOpenMany2XRecord({
                resModel,
                activeActions,
                isToMany,
                onRecordSaved: (record) => update([{ ...record.data, id: record.resId }]),
                onRecordDiscarded: () => {
                    if (!isToMany) {
                        this.props.update(false);
                    }
                },
                fieldString,
                onClose: () => {
                    const autoCompleteInput = this.autoCompleteContainer.el.querySelector("input");

                    // There are two cases:
                    // 1. Value is the same as the input: it means the autocomplete has re-rendered with the right value
                    //    This is in case we saved the record, triggering all the interface to update.
                    // 2. Value is different from the input: it means the input has a manually entered value and nothing
                    //    happened, that is, we discarded the changes
                    if (this.props.value !== autoCompleteInput.value) {
                        autoCompleteInput.value = "";
                    }
                    autoCompleteInput.focus();
                },
                component: this.createDialog,
                size: this.createDialogSize,
            });

        this.selectCreate = useSelectCreate({
            resModel,
            activeActions,
            onSelected: (resId) => {
                const resIds = Array.isArray(resId) ? resId : [resId];
                const values = resIds.map((id) => ({ id }));
                return update(values);
            },
            onCreateEdit: ({ context }) => this.openMany2X({ context }),
            onUnselect: isToMany ? undefined : () => update(),
        });
    }

    get autoCompleteProps() {
        return {
            autocomplete: "off",
            autoSelect: this.props.autoSelect,
            autofocus: this.props.autofocus,
            dropdown: this.props.dropdown,
            id: this.props.id,
            onCancel: this.onCancel.bind(this),
            onChange: this.onChange.bind(this),
            onInput: this.onInput.bind(this),
            placeholder: this.props.placeholder,
            resetOnSelect: this.props.value === "",
            sources: this.sources,
            slots: this.props.slots,
            value: this.props.value,
        };
    }

    get sources() {
        return [this.optionsSource, ...this.props.otherSources];
    }

    get optionsSource() {
        return {
            placeholder: _t("Loading..."),
            options: this.loadOptionsSource.bind(this),
            optionSlot: "option",
        };
    }

    get activeActions() {
        return this.props.activeActions || {};
    }

    get createDialog() {
        return FormViewDialog;
    }

    get createDialogSize() {
        return "lg";
    }

    getCreationContext(value) {
        return makeContext([
            this.props.context,
            value && { [`default_${this.props.nameCreateField}`]: value },
        ]);
    }
    onInput({ inputValue }) {
        if (!this.props.value || this.props.value !== inputValue) {
            this.props.setInputFloats(true);
        }
    }
    onCancel() {
        this.props.setInputFloats(false);
    }

    get searchSpecification() {
        return {
            display_name: {},
            ...this.props.specification,
        };
    }

    async search(name) {
        if (name.startsWith(this.lastEmptySearch) || name.length < this.props.searchThreshold) {
            return [];
        }
        const records = await this.orm.call(this.props.resModel, "web_name_search", [], {
            name,
            operator: "ilike",
            domain: this.props.getDomain(),
            limit: this.props.searchLimit + 1,
            context: this.props.context,
            specification: this.searchSpecification,
        });
        if (!records.length) {
            this.lastEmptySearch = name;
        }
        return records;
    }

    slowCreate(request) {
        return this.openMany2X({
            context: this.getCreationContext(request),
            nextRecordsContext: this.props.context,
        });
    }

    onQuickCreateError(error, request) {
        if (
            error instanceof RPCError &&
            error.exceptionName === "odoo.exceptions.ValidationError"
        ) {
            return this.slowCreate(request);
        } else {
            throw error;
        }
    }

    async loadOptionsSource(request) {
        await this.keepLast.add(Promise.resolve());
        return this.suggest(request, (promise) => this.keepLast.add(promise));
    }

    async suggest(request, lock) {
        const suggestions = [];
        /** @type {Record<string, any>[] | null} */
        let records = null;

        if (request.length < this.props.searchThreshold) {
            if (this.addStartTypingSuggestion({ request, records })) {
                suggestions.push(this.buildStartTypingSuggestion());
            }
        } else {
            records = await lock(this.search(request));
            if (records.length) {
                for (const record of records) {
                    suggestions.push(this.buildRecordSuggestion(request, record));
                }
            } else if (this.addNoRecordsSuggestion({ request, records })) {
                suggestions.push(this.buildNoRecordsSuggestion());
            } else if (this.addStartTypingSuggestion({ request, records })) {
                suggestions.push(this.buildStartTypingSuggestion());
            }
        }

        for (const action of this.actionSuggestions) {
            const enabled = action.enabled ?? (() => true);
            if (enabled({ request, records })) {
                suggestions.push(action.build(request));
            }
        }

        return suggestions;
    }

    get actionSuggestions() {
        return [
            {
                // create
                enabled: this.addCreateSuggestion.bind(this),
                build: this.buildCreateSuggestion.bind(this),
            },
            {
                // create and edit
                enabled: this.addCreateEditSuggestion.bind(this),
                build: this.buildCreateEditSuggestion.bind(this),
            },
            {
                // search more
                enabled: this.addSearchMoreSuggestion.bind(this),
                build: this.buildSearchMoreSuggestion.bind(this),
            },
        ];
    }

    addCreateSuggestion({ request }) {
        return !!this.props.quickCreate && request.length > 0;
    }

    addCreateEditSuggestion({ records, request }) {
        return (
            (this.activeActions.createEdit ?? this.activeActions.create) &&
            (request.length > 0 || records?.length === 0)
        );
    }

    addNoRecordsSuggestion({ request, records }) {
        return !this.activeActions.createEdit && !this.props.quickCreate;
    }

    addSearchMoreSuggestion({ records, request }) {
        return request.length < this.props.searchThreshold || records?.length > 0;
    }

    addStartTypingSuggestion({ request, records }) {
        return records !== null ? request.length === 0 && !this.activeActions.createEdit : !this.props.value;
    }

    buildCreateSuggestion(request) {
        return {
            cssClass: "o_m2o_dropdown_option o_m2o_dropdown_option_create",
            data: { slotName: "createItem" },
            label: _t('Create "%s"', request),
            onSelect: async () => {
                try {
                    await this.props.quickCreate(request);
                } catch (e) {
                    this.onQuickCreateError(e, request);
                }
            },
        };
    }

    buildCreateEditSuggestion(request) {
        return {
            cssClass: "o_m2o_dropdown_option o_m2o_dropdown_option_create_edit",
            data: { slotName: "createEditItem" },
            label: request.length > 0 ? _t("Create and edit...") : _t("Create..."),
            onSelect: () => this.slowCreate(request),
        };
    }

    buildNoRecordsSuggestion() {
        return {
            cssClass: "o_m2o_no_result",
            data: { slotName: "noRecordsItem" },
            label: _t("No records"),
        };
    }

    buildRecordSuggestion(request, record) {
        const label = record.__formatted_display_name || record.display_name;
        return {
            data: { record, slotName: "autoCompleteItem" },
            label: label
                ? highlightText(request, odoomark(label), "text-primary fw-bold")
                : _t("Unnamed"),
            onSelect: () => this.props.update([record]),
        };
    }

    buildSearchMoreSuggestion(request) {
        return {
            cssClass: "o_m2o_dropdown_option o_m2o_dropdown_option_search_more",
            data: { slotName: "searchMoreItem" },
            label: this.SearchMoreButtonLabel,
            onSelect: this.onSearchMore.bind(this, request),
        };
    }

    buildStartTypingSuggestion() {
        return {
            cssClass: "o_m2o_start_typing",
            data: { slotName: "startTypingItem" },
            label:
                this.props.searchThreshold > 1
                    ? _t("Start typing %s characters", this.props.searchThreshold)
                    : _t("Start typing..."),
        };
    }

    get SearchMoreButtonLabel() {
        return this.props.searchMoreLabel ?? _t("Search more...");
    }

    async onBarcodeSearch() {
        const autoCompleteInput = this.autoCompleteContainer.el.querySelector("input");
        return this.onSearchMore(autoCompleteInput.value);
    }

    async onSearchMore(request) {
        const { resModel, getDomain, context, fieldString } = this.props;

        const domain = getDomain();
        let dynamicFilters = [];
        if (request.length) {
            const nameGets = await this.orm.call(resModel, "name_search", [], {
                name: request,
                domain: domain,
                operator: "ilike",
                limit: this.props.searchMoreLimit,
                context,
            });

            dynamicFilters = [
                {
                    description: _t("Quick search: %s", request),
                    domain: [["id", "in", nameGets.map((nameGet) => nameGet[0])]],
                },
            ];
        }

        const title = _t("Search: %s", fieldString);
        this.selectCreate({
            domain,
            context,
            filters: dynamicFilters,
            title,
        });
    }

    onChange({ inputValue }) {
        if (!inputValue.length) {
            this.props.update(false);
        }
    }
}

export function useOpenMany2XRecord({
    resModel,
    onRecordSaved,
    onRecordDiscarded,
    fieldString,
    activeActions,
    isToMany,
    onClose = (isNew) => {},
    component = FormViewDialog,
    size = "lg",
}) {
    const addDialog = useOwnedDialogs();
    const orm = useService("orm");

    return async function openDialog(
        { resId = false, forceModel = null, title, context, nextRecordsContext },
        immediate = false
    ) {
        const model = forceModel || resModel;
        let viewId;
        if (resId !== false) {
            viewId = await orm.call(model, "get_formview_id", [[resId]], {
                context,
            });
        }

        let resolve = () => {};
        if (!title) {
            title = resId ? _t("Open: %s", fieldString) : _t("Create %s", fieldString);
        }

        const { create: canCreate, write: canWrite } = activeActions;
        const readonly = !(resId ? canWrite : canCreate);

        addDialog(
            component,
            {
                preventCreate: !canCreate,
                preventEdit: !canWrite,
                title,
                context,
                nextRecordsContext,
                readonly,
                resId,
                resModel: model,
                viewId,
                onRecordSaved,
                onRecordDiscarded,
                isToMany,
                size,
            },
            {
                onClose: () => {
                    resolve();
                    const isNew = !resId;
                    onClose(isNew);
                },
            }
        );

        if (!immediate) {
            return new Promise((_resolve) => {
                resolve = _resolve;
            });
        }
    };
}

//
// X2Many
//

export class X2ManyFieldDialog extends Component {
    static template = "web.X2ManyFieldDialog";
    static components = { Dialog, FormRenderer, ViewButton };
    static props = {
        archInfo: Object,
        close: Function,
        record: Object,
        addNew: Function,
        save: Function,
        title: String,
        delete: { optional: true },
        deleteButtonLabel: { optional: true },
        config: Object,
        controls: { type: Array, optional: true },
    };
    static defaultProps = {
        controls: [],
    };
    setup() {
        this.actionService = useService("action");
        this.archInfo = this.props.archInfo;
        this.record = this.props.record;
        this.title = this.props.title;
        this.contentClass = computeViewClassName("form", this.archInfo.xmlDoc);
        useSubEnv({ config: this.props.config });
        this.env.dialogData.dismiss = () => this.discard();

        useBus(this.record.model.bus, "update", () => this.render(true));

        this.modalRef = useChildRef();

        const reload = () => this.record.load();

        useViewButtons(this.modalRef, {
            reload,
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
        }); // maybe pass the model directly in props

        this.readonly = this.record.resId && !this.archInfo.activeActions.edit;
        this.canCreate = !this.record.resId;

        if (this.archInfo.xmlDoc.querySelector("footer:not(field footer)")) {
            this.archInfo = { ...this.archInfo, xmlDoc: this.archInfo.xmlDoc.cloneNode(true) };
            this.footerArchInfo = Object.assign({}, this.archInfo);
            this.footerArchInfo.xmlDoc = createElement("t");
            this.footerArchInfo.xmlDoc.append(
                ...this.archInfo.xmlDoc.querySelectorAll("footer:not(field footer)")
            );
            this.footerArchInfo.arch = this.footerArchInfo.xmlDoc.outerHTML;
            this.archInfo.arch = this.archInfo.xmlDoc.outerHTML;
        }

        const { autofocusFieldIds, disableAutofocus } = this.archInfo;
        if (!disableAutofocus) {
            // to simplify
            useEffect(
                (isInEdition) => {
                    let elementToFocus;
                    if (isInEdition) {
                        for (const id of autofocusFieldIds) {
                            elementToFocus = this.modalRef.el.querySelector(`#${id}`);
                            if (elementToFocus) {
                                break;
                            }
                        }
                        elementToFocus =
                            elementToFocus ||
                            this.modalRef.el.querySelector(".o_field_widget input");
                    } else {
                        elementToFocus = this.modalRef.el.querySelector("button.btn-primary");
                    }
                    if (elementToFocus) {
                        elementToFocus.focus();
                    } else {
                        this.modalRef.el.focus();
                    }
                },
                () => [this.record.isInEdition]
            );
        }
        useFormViewInDialog();
    }

    get dialogProps() {
        const props = {
            title: this.title,
            withBodyPadding: false,
            modalRef: this.modalRef,
            contentClass: this.contentClass,
        };
        if (!this.record.isNew) {
            props.onExpand = async () => {
                await this.save({ saveAndNew: false });
                this.actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: this.props.record.resModel,
                    res_id: this.props.record.resId,
                    views: [[false, "form"]],
                });
            };
        }
        return props;
    }

    get displayDeleteButton() {
        const deleteControl = this.props.controls.find((control) => control.type === "delete");
        return (
            !deleteControl || !evaluateBooleanExpr(deleteControl.invisible, this.record.evalContext)
        );
    }

    async beforeExecuteActionButton(clickParams) {
        if (clickParams.special !== "cancel") {
            return this.record.save();
        }
    }

    async discard() {
        if (this.record.isInEdition) {
            await this.record.discard();
        }
        this.props.close();
    }

    save({ saveAndNew }) {
        return executeButtonCallback(this.modalRef.el, async () => {
            if (await this.record.checkValidity({ displayNotification: true })) {
                await this.props.save(this.record);
                if (saveAndNew) {
                    await this.record.switchMode("readonly");
                    this.record = await this.props.addNew();
                }
            } else {
                return false;
            }
            if (!saveAndNew) {
                this.props.close();
            }
            return true;
        });
    }

    async remove() {
        await this.props.delete();
        this.props.close();
    }

    async saveAndNew() {
        const saved = await this.save({ saveAndNew: true });
        if (saved) {
            if (this.title) {
                this.title = this.title.replace(_t("Open:"), _t("New:"));
            }
            this.render(true);
        }
    }
}

async function getFormViewInfo({ list, context, activeField, viewService, env }) {
    let formArchInfo = activeField.views.form;
    let fields = activeField.fields;
    const comodel = list.resModel;
    if (!formArchInfo) {
        const {
            fields: formFields,
            relatedModels,
            views,
        } = await viewService.loadViews({
            context: makeContext([list.context, context]),
            resModel: comodel,
            views: [[false, "form"]],
        });
        const xmlDoc = parseXML(views.form.arch);
        formArchInfo = new FormArchParser().parse(xmlDoc, relatedModels, comodel);
        // Fields that need to be defined are the ones in the form view, this is natural,
        // plus the ones that the list record has, that is, present in either the list arch
        // or the kanban arch of the one2many field
        fields = { ...list.fields, ...formFields }; // FIXME: update in place?
    }

    await loadSubViews(
        formArchInfo.fieldNodes,
        fields,
        {}, // context
        comodel,
        viewService,
        env.isSmall
    );

    return { archInfo: formArchInfo, fields };
}

export function useAddInlineRecord({ addNew }) {
    let creatingRecord = false;

    async function addInlineRecord({ context, editable }) {
        if (!creatingRecord) {
            creatingRecord = true;
            try {
                await addNew({ context, mode: "edit", position: editable });
            } finally {
                creatingRecord = false;
            }
        }
    }
    return addInlineRecord;
}

export function useOpenX2ManyRecord({
    activeField, // TODO: this should be renamed (object with keys "viewMode", "views" and "string")
    activeActions,
    getList,
    updateRecord,
    saveRecord,
    isMany2Many,
}) {
    const viewService = useService("view");
    const env = useEnv();
    const component = useComponent();

    const addDialog = useOwnedDialogs();
    const viewMode = activeField.viewMode;

    async function openRecord({ record, readonly, context, title, controls, onClose }) {
        if (!title) {
            title = record
                ? _t("Open: %s", activeField.string)
                : _t("Create %s", activeField.string);
        }
        const list = getList();
        const { archInfo, fields: _fields } = await getFormViewInfo({
            list,
            context,
            activeField,
            viewService,
            env,
        });
        if (!component.props.record.isInEdition) {
            archInfo.activeActions.edit = false;
        }

        const { activeFields, fields } = extractFieldsFromArchInfo(archInfo, _fields);

        let deleteRecord;
        let deleteButtonLabel = undefined;
        const isDuplicate = !!record;

        const params = { activeFields, fields, readonly };
        params.mode = params.readonly ? "readonly" : "edit";
        if (record) {
            const { delete: canDelete, onDelete } = activeActions;
            deleteRecord = viewMode === "kanban" && canDelete ? () => onDelete(record) : null;
            deleteButtonLabel = activeActions.type === "one2many" ? _t("Delete") : _t("Remove");
        } else {
            params.context = makeContext([list.context, context]);
            params.withoutParent = isMany2Many;
        }
        record = await list.extendRecord(params, record);

        const _onClose = () => {
            list.editedRecord?.switchMode("readonly");
            onClose?.();
        };

        addDialog(
            X2ManyFieldDialog,
            {
                config: env.config,
                archInfo,
                record,
                controls,
                addNew: () => getList().extendRecord(params),
                save: (rec) => {
                    if (isDuplicate && rec.id === record.id) {
                        return updateRecord(rec);
                    } else {
                        return saveRecord(rec);
                    }
                },
                title,
                delete: deleteRecord,
                deleteButtonLabel: deleteButtonLabel,
            },
            { onClose: _onClose }
        );
    }

    let recordIsOpen = false;
    return (params) => {
        if (recordIsOpen) {
            return;
        }
        recordIsOpen = true;

        const onClose = params.onClose;
        params = {
            ...params,
            onClose: (...args) => {
                recordIsOpen = false;
                if (onClose) {
                    return onClose(...args);
                }
            },
        };

        try {
            return openRecord(params);
        } catch (e) {
            recordIsOpen = false;
            throw e;
        }
    };
}

export function useX2ManyCrud(getList, isMany2Many) {
    let saveRecord; // FIXME: isn't this "createRecord" instead?
    if (isMany2Many) {
        saveRecord = async (object) => {
            const list = getList();
            if (Array.isArray(object)) {
                return list.addAndRemove({ add: object });
            } else {
                // object instanceof Record
                await object.save({ reload: false });
                return list.linkTo(object.resId);
            }
        };
    } else {
        saveRecord = async (record) => getList().validateExtendedRecord(record);
    }

    const updateRecord = async (record) => {
        if (isMany2Many) {
            await record.save();
        }
        return getList().validateExtendedRecord(record);
    };

    const removeRecord = (record) => {
        const list = getList();
        if (isMany2Many) {
            return list.forget(record);
        }
        return list.delete(record);
    };

    return {
        saveRecord,
        updateRecord,
        removeRecord,
    };
}
