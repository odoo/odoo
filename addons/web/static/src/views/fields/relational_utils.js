/** @odoo-module */

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { makeContext } from "@web/core/context";
import { Dialog } from "@web/core/dialog/dialog";
import {
    useBus,
    useChildRef,
    useForwardRefToParent,
    useOwnedDialogs,
    useService,
} from "@web/core/utils/hooks";
import { createElement } from "@web/core/utils/xml";
import { sprintf } from "@web/core/utils/strings";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { loadSubViews } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { evalDomain } from "@web/views/utils";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

const { useEffect } = owl;

//
// Commons
//
export function useSelectCreate({ resModel, activeActions, onSelected, onCreateEdit }) {
    const env = owl.useEnv();
    const addDialog = useOwnedDialogs();

    function selectCreate({ domain, context, filters, title }) {
        addDialog(SelectCreateDialog, {
            title: title || env._t("Select records"),
            noCreate: !activeActions.canCreate,
            multiSelect: "canLink" in activeActions ? activeActions.canLink : false, // LPE Fixme
            resModel,
            context,
            domain,
            onSelected,
            onCreateEdit: () => onCreateEdit({ context }),
            dynamicFilters: filters,
        });
    }
    return selectCreate;
}

const STANDARD_ACTIVE_ACTIONS = ["create", "delete", "link", "unlink", "write"];
export function useActiveActions({
    subViewActiveActions = {},
    crudOptions = {},
    fieldType,
    getEvalParams = (props) => ({}),
}) {
    const props = owl.useComponent().props;

    const evals = {};
    const makeEvalAction = (actionName, defaultBool = true) => {
        let evalFn;
        if (crudOptions[actionName] !== undefined) {
            const action = crudOptions[actionName];
            evalFn = (evalContext) => evalDomain(action, evalContext);
        } else {
            evalFn = () => defaultBool;
        }

        if (actionName in subViewActiveActions) {
            const viewActiveAction = subViewActiveActions[actionName];
            evals[actionName] = (evalContext) => viewActiveAction && evalFn(evalContext);
            return;
        }
        evals[actionName] = evalFn;
    };

    function evalAction(actionName, evalContext) {
        return evals[actionName](evalContext);
    }

    for (const actionName of STANDARD_ACTIVE_ACTIONS) {
        makeEvalAction(actionName, actionName !== "write");
    }

    const isMany2Many = fieldType === "many2many";
    const isMany2One = fieldType === "many2one";

    function compute({ evalContext = {}, readonly = true }) {
        // activeActions computed by getActiveActions is of the form
        // interface ActiveActions {
        //     edit: Boolean;
        //     create: Boolean;
        //     delete: Boolean;
        //     duplicate: Boolean;
        // }

        // options set on field is of the form
        // interface Options {
        //     create: Boolean;
        //     delete: Boolean;
        //     link: Boolean;
        //     unlink: Boolean;
        // }

        // We need to take care of tags "control" and "create" to set create stuff
        const canCreate = !readonly && evalAction("create", evalContext);
        const canDelete = !readonly && evalAction("delete", evalContext);

        const canLink = !readonly && evalAction("link", evalContext);
        const canUnlink = !readonly && evalAction("unlink", evalContext);

        const result = { canCreate, canDelete };

        if (isMany2Many) {
            const canWrite = evalAction("write", evalContext);
            Object.assign(result, { canLink, canUnlink, canWrite });
        }

        if (isMany2One) {
            Object.assign(result, {
                canWrite: evalAction("write", evalContext),
                canCreateEdit: evalAction("createEdit", evalContext),
            });
        }

        if ((isMany2Many && canUnlink) || (!isMany2Many && canDelete)) {
            result.onDelete = crudOptions.onDelete;
        }
        return result;
    }

    let activeActions = compute(getEvalParams(props));

    owl.onWillUpdateProps((nextProps) => {
        activeActions = compute(getEvalParams(nextProps));
    });

    return new Proxy(
        {},
        {
            get(target, k) {
                return activeActions[k];
            },
            has(target, k) {
                return k in activeActions;
            },
        }
    );
}

//
// Many2X
//

export class Many2XAutocomplete extends owl.Component {
    setup() {
        this.orm = useService("orm");

        const autoCompleteContainer = useForwardRefToParent("autocomplete_container");

        this.state = owl.useState({
            autocompleteValue: this.props.value,
        });

        const { activeActions, resModel, update, isToMany, fieldString } = this.props;

        this.openMany2X = useOpenMany2XRecord({
            resModel,
            activeActions,
            isToMany,
            onRecordSaved: (record) => {
                return update([record.data]);
            },
            fieldString,
            onClose: () => {
                autoCompleteContainer.el.querySelector("input").focus();
            },
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
        });

        this.forceClose = false;
        owl.onWillUpdateProps((nextProps) => {
            this.state.autocompleteValue = nextProps.value;
            if (this.preventClose) {
                return;
            }
            this.forceClose = true;
        });
        owl.useEffect(() => {
            this.forceClose = false;
            this.preventClose = false;
        });
    }

    get sources() {
        return [this.optionsSource];
    }
    get optionsSource() {
        return {
            placeholder: this.env._t("Loading..."),
            options: this.loadOptionsSource.bind(this),
        };
    }

    get activeActions() {
        return this.props.activeActions;
    }

    getCreationContext(value) {
        return makeContext([
            this.props.context,
            { [`default_${this.props.nameCreateField}`]: value },
        ]);
    }
    onInput({ inputValue }) {
        if (!this.props.value || this.props.value !== inputValue) {
            this.preventClose = true;
            this.props.setInputFloats(true);
        }
    }

    onSelect(option, params = {}) {
        if (option.action) {
            return option.action(params);
        }
        this.state.autocompleteValue = "";
        const record = {
            id: option.value,
            name: option.label,
        };
        this.props.update([record], params);
    }

    async loadOptionsSource(request) {
        const records = await this.orm.call(this.props.resModel, "name_search", [], {
            name: request,
            operator: "ilike",
            args: this.props.getDomain(),
            limit: this.props.searchLimit + 1,
            context: this.props.context,
        });

        const options = records.map((result) => ({
            value: result[0],
            label: result[1],
        }));

        if (this.props.quickCreate && request.length) {
            options.push({
                label: sprintf(this.env._t(`Create "%s"`), request),
                classList: "o_m2o_dropdown_option o_m2o_dropdown_option_create",
                action: async (params) => {
                    try {
                        await this.props.quickCreate(request, params);
                    } catch {
                        const context = this.getCreationContext(request);
                        return this.openMany2X({ context });
                    }
                },
            });
        }

        if (this.props.searchLimit < records.length) {
            options.push({
                label: this.env._t("Search More..."),
                action: this.onSearchMore.bind(this, request),
                classList: "o_m2o_dropdown_option o_m2o_dropdown_option_search_more",
            });
        }

        const activeActions = this.activeActions;
        const canCreateEdit =
            "canCreateEdit" in activeActions
                ? activeActions.canCreateEdit
                : activeActions.canCreate;
        if (!request.length && !this.props.value && (this.props.quickCreate || canCreateEdit)) {
            options.push({
                label: this.env._t("Start typing..."),
                classList: "o_m2o_start_typing",
                unselectable: true,
            });
        }

        if (request.length && canCreateEdit) {
            const context = this.getCreationContext(request);
            options.push({
                label: this.env._t("Create and edit..."),
                classList: "o_m2o_dropdown_option o_m2o_dropdown_option_create_edit",
                action: () => this.openMany2X({ context }),
            });
        }

        if (!records.length && !activeActions.canCreate) {
            options.push({
                label: this.env._t("No records"),
                classList: "o_m2o_no_result",
                unselectable: true,
            });
        }

        return options;
    }

    async onSearchMore(request) {
        const { resModel, getDomain, context, fieldString } = this.props;

        const domain = getDomain();
        let dynamicFilters = [];
        if (request.length) {
            const nameGets = await this.orm.call(resModel, "name_search", [], {
                name: request,
                args: domain,
                operator: "ilike",
                limit: this.props.searchMoreLimit,
                context,
            });

            dynamicFilters = [
                {
                    description: sprintf(this.env._t("Quick search: %s"), request),
                    domain: [["id", "in", nameGets.map((nameGet) => nameGet[0])]],
                },
            ];
        }

        const title = sprintf(this.env._t("Search: %s"), fieldString);
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
Many2XAutocomplete.template = "web.Many2XAutocomplete";
Many2XAutocomplete.components = { AutoComplete };
Many2XAutocomplete.defaultProps = {
    searchLimit: 7,
    searchMoreLimit: 320,
    nameCreateField: "name",
    value: "",
    setInputFloats: () => {},
    quickCreate: null,
};

export function useOpenMany2XRecord({
    resModel,
    onRecordSaved,
    fieldString,
    activeActions,
    isToMany,
    onClose = (isNew) => {},
}) {
    const env = owl.useEnv();
    const addDialog = useOwnedDialogs();
    const orm = useService("orm");

    return async function openDialog({ resId = false, title, context }, immediate = false) {
        let viewId;
        if (resId !== false) {
            viewId = await orm.call(resModel, "get_formview_id", [[resId]], {
                context,
            });
        }

        let resolve = () => {};
        if (!title) {
            title = resId ? env._t("Open: %s") : env._t("Create %s");
            title = sprintf(title, fieldString);
        }

        const { canCreate, canWrite } = activeActions;

        const mode = (resId ? canWrite : canCreate) ? "edit" : "readonly";

        addDialog(
            FormViewDialog,
            {
                preventCreate: !activeActions.canCreate,
                preventEdit: !activeActions.canWrite,
                title,
                context,
                mode,
                resId,
                resModel,
                viewId,
                onRecordSaved,
                isToMany,
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

class X2ManyFieldDialog extends owl.Component {
    setup() {
        this.archInfo = this.props.archInfo;
        this.record = this.props.record;
        this.title = this.props.title;

        useBus(this.record.model, "update", () => this.render(true));

        this.modalRef = useChildRef();

        const reload = () => this.record.load();
        useViewButtons(this.props.record.model, this.modalRef, { reload }); // maybe pass the model directly in props

        if (this.archInfo.xmlDoc.querySelector("footer")) {
            this.footerArchInfo = Object.assign({}, this.archInfo);
            this.footerArchInfo.xmlDoc = createElement("t");
            this.footerArchInfo.xmlDoc.append(
                ...[...this.archInfo.xmlDoc.querySelectorAll("footer")]
            );
            this.footerArchInfo.arch = this.footerArchInfo.xmlDoc.outerHTML;
            [...this.archInfo.xmlDoc.querySelectorAll("footer")].forEach((x) => x.remove());
            this.archInfo.arch = this.archInfo.xmlDoc.outerHTML;
        }

        const { autofocusFieldId, disableAutofocus } = this.archInfo;
        if (!disableAutofocus) {
            // to simplify
            useEffect(
                (isInEdition) => {
                    let elementToFocus;
                    if (isInEdition) {
                        elementToFocus =
                            (autofocusFieldId &&
                                this.modalRef.el.querySelector(`#${autofocusFieldId}`)) ||
                            this.modalRef.el.querySelector(".o_field_widget input");
                    } else {
                        elementToFocus =
                            this.modalRef.el.querySelector("button.btn-primary") ||
                            this.modalRef.el.querySelector(".o_control_panel .o_form_button_edit");
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
    }

    disableButtons() {
        const btns = this.modalRef.el.querySelectorAll(".modal-footer button");
        for (const btn of btns) {
            btn.setAttribute("disabled", "1");
        }
        return btns;
    }

    discard() {
        if (this.record.isInEdition) {
            this.record.discard();
        }
        this.props.close();
    }

    enableButtons(btns) {
        for (const btn of btns) {
            btn.removeAttribute("disabled");
        }
    }

    async save({ saveAndNew }) {
        if (this.record.checkValidity()) {
            this.record = (await this.props.save(this.record, { saveAndNew })) || this.record;
        } else {
            return false;
        }
        if (!saveAndNew) {
            this.props.close();
        }
        return true;
    }

    async remove() {
        await this.props.delete();
        this.props.close();
    }

    async saveAndNew() {
        const disabledButtons = this.disableButtons();
        const saved = await this.save({ saveAndNew: true });
        if (saved) {
            this.enableButtons(disabledButtons);
            if (this.title) {
                this.title = this.title.replace(this.env._t("Open:"), this.env._t("New:"));
            }
            this.render(true);
        }
    }
}
X2ManyFieldDialog.components = { Dialog, FormRenderer, ViewButton };
X2ManyFieldDialog.props = {
    archInfo: Object,
    close: Function,
    record: Object,
    save: Function,
    title: String,
    delete: { optional: true },
};
X2ManyFieldDialog.template = "web.X2ManyFieldDialog";

async function getFormViewInfo({ list, activeField, viewService, userService, env }) {
    let formViewInfo = activeField.views.form;
    const comodel = list.resModel;
    if (!formViewInfo) {
        const { fields, relatedModels, views } = await viewService.loadViews({
            context: {},
            resModel: comodel,
            views: [[false, "form"]],
        });
        const archInfo = new FormArchParser().parse(views.form.arch, relatedModels, comodel);
        formViewInfo = { ...archInfo, fields }; // should be good to memorize this on activeField
    }

    await loadSubViews(
        formViewInfo.activeFields,
        formViewInfo.fields,
        {}, // context
        comodel,
        viewService,
        userService,
        env.isSmall
    );

    return formViewInfo;
}

export function useAddInlineRecord({ position, addNew }) {
    let creatingRecord = false;

    async function addInlineRecord({ context }) {
        if (!creatingRecord) {
            creatingRecord = true;
            try {
                await addNew({ context, mode: "edit", position });
            } finally {
                creatingRecord = false;
            }
        }
    }
    return addInlineRecord;
}

export function useOpenX2ManyRecord({
    resModel,
    activeField,
    activeActions,
    getList,
    updateRecord,
    saveRecord,
}) {
    const viewService = useService("view");
    const userService = useService("user");
    const env = owl.useEnv();

    const addDialog = useOwnedDialogs();
    const viewMode = activeField.viewMode;

    async function openRecord({ record, mode, context, title, onClose }) {
        if (!title) {
            title = record ? env._t("Open: %s") : env._t("Create %s");
            title = sprintf(title, activeField.string);
        }
        const list = getList();
        const model = list.model;
        const form = await getFormViewInfo({ list, activeField, viewService, userService, env });

        let deleteRecord;
        const isDuplicate = !!record;

        if (record) {
            const _record = record;
            record = await model.duplicateDatapoint(record, {
                mode,
                viewMode: "form",
                fields: { ...form.fields },
                views: { form },
            });
            const { canDelete, onDelete } = activeActions;
            deleteRecord = viewMode === "kanban" && canDelete ? () => onDelete(_record) : null;
        } else {
            const recordParams = {
                context: makeContext([list.context, context]),
                resModel: resModel,
                activeFields: form.activeFields,
                fields: { ...form.fields },
                views: { form },
                mode: "edit",
                viewType: "form",
            };
            record = await model.addNewRecord(list, recordParams);
        }

        addDialog(
            X2ManyFieldDialog,
            {
                archInfo: form,
                record,
                save: async (rec, { saveAndNew }) => {
                    if (isDuplicate && rec.id === record.id) {
                        await updateRecord(rec);
                    } else {
                        await saveRecord(rec);
                    }
                    if (saveAndNew) {
                        return model.addNewRecord(list, {
                            context: list.context,
                            resModel: resModel,
                            activeFields: form.activeFields,
                            fields: { ...form.fields },
                            views: { form },
                            mode: "edit",
                            viewType: "form",
                        });
                    }
                },
                title,
                delete: deleteRecord,
            },
            { onClose }
        );
    }
    return openRecord;
}

export function useX2ManyCrud(getList, isMany2Many) {
    let saveRecord;
    if (isMany2Many) {
        saveRecord = (object) => {
            const list = getList();
            const currentIds = list.currentIds;
            let resIds;
            if (Array.isArray(object)) {
                resIds = [...currentIds, ...object];
            } else if (object.resId) {
                resIds = [...currentIds, object.resId];
            } else {
                return list.add(object, { isM2M: isMany2Many });
            }
            return list.replaceWith(resIds);
        };
    } else {
        saveRecord = (record) => {
            return getList().add(record);
        };
    }

    const updateRecord = (record) => {
        const list = getList();
        return list.model.updateRecord(list, record, { isM2M: isMany2Many });
    };

    const operation = isMany2Many ? "FORGET" : "DELETE";
    const removeRecord = (record) => {
        const list = getList();
        return list.delete(record.id, operation);
    };

    return {
        saveRecord,
        updateRecord,
        removeRecord,
    };
}
