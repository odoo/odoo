import { _t } from "@web/core/l10n/translation";
import { hasTouch } from "@web/core/browser/feature_detection";
import {
    deleteConfirmationMessage,
    ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeContext } from "@web/core/context";
import { useDebugCategory } from "@web/core/debug/debug_context";
import { registry } from "@web/core/registry";
import { SIZES } from "@web/core/ui/ui_service";
import { user } from "@web/core/user";
import { useBus, useService } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";
import { createElement, parseXML } from "@web/core/utils/xml";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { useSetupAction } from "@web/search/action_hook";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { standardViewProps } from "@web/views/standard_view_props";
import { isX2Many } from "@web/views/utils";
import { executeButtonCallback, useViewButtons } from "@web/views/view_button/view_button_hook";
import { ViewButton } from "@web/views/view_button/view_button";
import { Field } from "@web/views/fields/field";
import { useModel } from "@web/model/model";
import { addFieldDependencies, extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { useViewCompiler } from "@web/views/view_compiler";
import { Widget } from "@web/views/widgets/widget";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

import { ButtonBox } from "./button_box/button_box";
import { FormCompiler } from "./form_compiler";
import { FormErrorDialog } from "./form_error_dialog/form_error_dialog";
import { FormStatusIndicator } from "./form_status_indicator/form_status_indicator";
import { StatusBarDropdownItems } from "./status_bar_dropdown_items/status_bar_dropdown_items";
import { FormCogMenu } from "./form_cog_menu/form_cog_menu";

import {
    Component,
    onError,
    onMounted,
    onRendered,
    onWillUnmount,
    status,
    useComponent,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { FetchRecordError } from "@web/model/relational_model/errors";
import { effect } from "@web/core/utils/reactive";

const viewRegistry = registry.category("views");

export async function loadSubViews(fieldNodes, fields, context, resModel, viewService, isSmall) {
    for (const fieldInfo of Object.values(fieldNodes)) {
        const fieldName = fieldInfo.name;
        const field = fields[fieldName];
        if (!isX2Many(field)) {
            continue; // what follows only concerns x2many fields
        }
        if (fieldInfo.invisible === "True" || fieldInfo.invisible === "1") {
            continue; // no need to fetch the sub view if the field is always invisible
        }
        if (!fieldInfo.field.useSubView) {
            continue; // the FieldComponent used to render the field doesn't need a sub view
        }

        fieldInfo.views = fieldInfo.views || {};
        let viewType = fieldInfo.viewMode || "list,kanban";
        if (viewType.includes(",")) {
            viewType = isSmall ? "kanban" : "list";
        }
        fieldInfo.viewMode = viewType;
        if (fieldInfo.views[viewType]) {
            continue; // the sub view is inline in the main form view
        }

        // extract *_view_ref keys from field context, to fetch the adequate view
        const fieldContext = {};
        const regex = /'([a-z]*_view_ref)' *: *'(.*?)'/g;
        let matches;
        while ((matches = regex.exec(fieldInfo.context)) !== null) {
            fieldContext[matches[1]] = matches[2];
        }
        // filter out *_view_ref keys from general context
        const refinedContext = {};
        for (const key in context) {
            if (key.indexOf("_view_ref") === -1) {
                refinedContext[key] = context[key];
            }
        }

        const comodel = field.relation;
        const {
            fields: comodelFields,
            relatedModels,
            views,
        } = await viewService.loadViews({
            resModel: comodel,
            views: [[false, viewType]],
            context: makeContext([fieldContext, user.context, refinedContext]),
        });
        const { ArchParser } = viewRegistry.get(viewType);
        const xmlDoc = parseXML(views[viewType].arch);
        const archInfo = new ArchParser().parse(xmlDoc, relatedModels, comodel);
        fieldInfo.views[viewType] = {
            ...archInfo,
            limit: archInfo.limit || 40,
            fields: comodelFields,
        };
        fieldInfo.relatedFields = comodelFields;
    }
}

export function useFormViewInDialog() {
    const component = useComponent();
    onMounted(() => {
        component.env.bus.trigger("FORM-CONTROLLER:FORM-IN-DIALOG:ADD");
    });

    onWillUnmount(() => {
        component.env.bus.trigger("FORM-CONTROLLER:FORM-IN-DIALOG:REMOVE");
    });
}
// -----------------------------------------------------------------------------

export class FormController extends Component {
    static template = `web.FormView`;
    static components = {
        FormStatusIndicator,
        Layout,
        ButtonBox,
        ViewButton,
        Field,
        CogMenu: FormCogMenu,
        StatusBarDropdownItems,
        Widget,
    };

    static props = {
        ...standardViewProps,
        discardRecord: { type: Function, optional: true },
        mode: {
            optional: true,
            validate: (m) => ["edit", "readonly"].includes(m),
        },
        saveRecord: { type: Function, optional: true },
        removeRecord: { type: Function, optional: true },
        Model: Function,
        Renderer: Function,
        Compiler: Function,
        archInfo: Object,
        buttonTemplate: String,
        preventCreate: { type: Boolean, optional: true },
        preventEdit: { type: Boolean, optional: true },
        onDiscard: { type: Function, optional: true },
        onSave: { type: Function, optional: true },
    };
    static defaultProps = {
        preventCreate: false,
        preventEdit: false,
        updateActionState: () => {},
    };

    setup() {
        this.evaluateBooleanExpr = evaluateBooleanExpr;
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.viewService = useService("view");
        this.ui = useService("ui");
        this.companyService = useService("company");
        useBus(this.ui.bus, "resize", this.render);

        this.archInfo = this.props.archInfo;
        const { create, edit } = this.archInfo.activeActions;
        this.canCreate = create && !this.props.preventCreate;
        this.canEdit = edit && !this.props.preventEdit;
        this.duplicateId = false;

        this.display = { ...this.props.display };
        if (this.env.inDialog) {
            this.display.controlPanel = false;
        }

        this.formInDialog = 0;

        useBus(this.env.bus, "FORM-CONTROLLER:FORM-IN-DIALOG:ADD", () => this.formInDialog++);
        useBus(this.env.bus, "FORM-CONTROLLER:FORM-IN-DIALOG:REMOVE", () => this.formInDialog--);

        const beforeFirstLoad = async () => {
            await loadSubViews(
                this.archInfo.fieldNodes,
                this.props.fields,
                this.props.context,
                this.props.resModel,
                this.viewService,
                this.env.isSmall
            );
            const { activeFields, fields } = extractFieldsFromArchInfo(
                this.archInfo,
                this.props.fields
            );
            if (this.display.controlPanel) {
                addFieldDependencies(activeFields, fields, [
                    { name: "display_name", type: "char", readonly: true },
                ]);
            }
            this.model.config.activeFields = activeFields;
            this.model.config.fields = fields;
        };
        this.model = useState(useModel(this.props.Model, this.modelParams, { beforeFirstLoad }));

        onMounted(() => {
            effect(
                (model) => {
                    if (status(this) === "mounted") {
                        this.props.updateActionState({ resId: model.root.resId });
                    }
                },
                [this.model]
            );
        });

        onError((error) => {
            const suggestedCompany = error.cause?.data?.context?.suggested_company;
            if (
                error.cause?.data?.name === "odoo.exceptions.AccessError" &&
                suggestedCompany &&
                !this.env.inDialog
            ) {
                this.env.pushStateBeforeReload();
                const activeCompanyIds = this.companyService.activeCompanyIds;
                activeCompanyIds.push(suggestedCompany.id);
                this.companyService.setCompanies(activeCompanyIds, true);
            } else {
                throw error;
            }
        });

        // select footers that are not in subviews and move them to another arch
        // that will be moved to the dialog's footer (if we are in a dialog)
        const footers = [...this.archInfo.xmlDoc.querySelectorAll("footer:not(field footer)")];
        if (footers.length) {
            this.footerArchInfo = Object.assign({}, this.archInfo);
            this.footerArchInfo.xmlDoc = createElement("t");
            this.footerArchInfo.xmlDoc.append(...footers);
            this.footerArchInfo.arch = this.footerArchInfo.xmlDoc.outerHTML;
            this.archInfo.arch = this.archInfo.xmlDoc.outerHTML;
        }

        const xmlDocButtonBox = this.archInfo.xmlDoc.querySelector(
            "div[name='button_box']:not(field div)"
        );
        if (xmlDocButtonBox) {
            const buttonBoxTemplates = useViewCompiler(
                this.props.Compiler || FormCompiler,
                { ButtonBox: xmlDocButtonBox },
                { isSubView: true }
            );
            this.buttonBoxTemplate = buttonBoxTemplates.ButtonBox;
        }

        const xmlDocHeader = this.archInfo.xmlDoc.querySelector("header");
        if (xmlDocHeader) {
            const { StatusBarDropdownItems } = useViewCompiler(
                this.props.Compiler || FormCompiler,
                { StatusBarDropdownItems: xmlDocHeader },
                { isSubView: true, asDropdownItems: true }
            );
            this.statusBarDropdownItemsTemplate = StatusBarDropdownItems;
        }

        this.rootRef = useRef("root");
        useViewButtons(this.rootRef, {
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
            reload: () => this.model.load(),
        });

        const state = this.props.state || {};
        const activeNotebookPages = { ...state.activeNotebookPages };
        this.onNotebookPageChange = (notebookId, page) => {
            if (page) {
                activeNotebookPages[notebookId] = page;
            }
        };

        useSetupAction({
            rootRef: this.rootRef,
            beforeVisibilityChange: () => this.beforeVisibilityChange(),
            beforeLeave: () => this.beforeLeave(),
            beforeUnload: (ev) => this.beforeUnload(ev),
            getLocalState: () => {
                return {
                    activeNotebookPages: !this.model.root.isNew ? activeNotebookPages : {},
                    modelState: this.model.exportState(),
                    resId: this.model.root.resId,
                };
            },
        });
        useDebugCategory("form", { component: this });

        usePager(() => {
            if (!this.model.root.isNew) {
                const resIds = this.model.root.resIds;
                return {
                    offset: resIds.indexOf(this.model.root.resId),
                    limit: 1,
                    total: resIds.length,
                    onUpdate: ({ offset }) => this.onPagerUpdate({ offset, resIds }),
                };
            }
        });

        onRendered(() => {
            this.env.config.setDisplayName(this.displayName());
        });

        const { disableAutofocus } = this.archInfo;
        if (!disableAutofocus) {
            useEffect(
                (isInEdition) => {
                    if (
                        !isInEdition &&
                        !this.rootRef.el
                            .querySelector(".o_content")
                            .contains(document.activeElement)
                    ) {
                        const elementToFocus = this.rootRef.el.querySelector(
                            ".o_content button.btn-primary"
                        );
                        if (elementToFocus) {
                            elementToFocus.focus();
                        }
                    }
                },
                () => [this.model.root.isInEdition]
            );
        }

        if (this.env.inDialog) {
            useFormViewInDialog();
        }
    }

    get cogMenuProps() {
        return {
            getActiveIds: () => (this.model.root.isNew ? [] : [this.model.root.resId]),
            context: this.props.context,
            items: this.props.info.actionMenus ? this.actionMenuItems : {},
            isDomainSelected: this.model.root.isDomainSelected,
            resModel: this.model.root.resModel,
            domain: this.props.domain,
            onActionExecuted: () =>
                this.model.load({ resId: this.model.root.resId, resIds: this.model.root.resIds }),
            shouldExecuteAction: this.shouldExecuteAction.bind(this),
        };
    }

    get modelParams() {
        let mode = this.props.mode || "edit";
        if (!this.canEdit && this.props.resId) {
            mode = "readonly";
        }
        return {
            config: {
                resModel: this.props.resModel,
                resId: this.props.resId || false,
                resIds: this.props.resIds || (this.props.resId ? [this.props.resId] : []),
                fields: this.props.fields,
                activeFields: {}, // will be generated after loading sub views (see willStart)
                isMonoRecord: true,
                mode,
                context: this.props.context,
            },
            state: this.props.state?.modelState,
            hooks: {
                onWillLoadRoot: this.onWillLoadRoot.bind(this),
                onWillSaveRecord: this.onWillSaveRecord.bind(this),
                onRecordSaved: this.onRecordSaved.bind(this),
            },
            useSendBeaconToSaveUrgently: true,
        };
    }

    /**
     * onWillLoadRoot is a callback that will be executed before (re)loading the
     * data necessary for the root record datapoint. Note that this.model.root
     * may not exist yet at this point, if this is the first load.
     */
    onWillLoadRoot() {
        this.duplicateId = undefined;
    }

    /**
     * onRecordSaved is a callBack that will be executed after the save
     * if it was done. It will therefore not be executed if the record
     * is invalid, if a server error is thrown, or if there are no
     * changes to save.
     * @param {Record} record
     */
    async onRecordSaved(record, changes) {
        if (this.duplicateId === record.id) {
            const translationChanges = {};
            for (const fieldName in changes) {
                if (record.fields[fieldName].translate) {
                    translationChanges[fieldName] = changes[fieldName];
                }
            }
            if (Object.keys(translationChanges).length) {
                await this.orm.call(this.model.root.resModel, "web_override_translations", [
                    [this.model.root.resId],
                    translationChanges,
                ]);
            }
        }
    }

    /**
     * onWillSaveRecord is a callBack that will be executed before the
     * record save if the record is valid if the record is valid.
     * If it returns false, it will prevent the save.
     * @param {Record} record
     */
    async onWillSaveRecord() {}

    async onSaveError(error, { discard }) {
        const proceed = await new Promise((resolve) => {
            this.model.dialog.add(FormErrorDialog, {
                message: error.data.message,
                data: error.data,
                onDiscard: () => {
                    discard();
                    resolve(true);
                },
                onRedirect: async ({ action, additionalContext }) => {
                    this.allowLeavingWithoutSaving = true;
                    try {
                        await this.actionService.doAction(action, {
                            additionalContext,
                        });
                    } finally {
                        this.allowLeavingWithoutSaving = false;
                        resolve(false);
                    }
                },
                onStayHere: () => resolve(false),
            });
        });
        return proceed;
    }

    displayName() {
        return this.model.root.data.display_name || (this.model.root.isNew && _t("New")) || "";
    }

    async onPagerUpdate({ offset, resIds }) {
        const dirty = await this.model.root.isDirty();
        try {
            if (dirty) {
                await this.model.root.save({
                    onError: this.onSaveError.bind(this),
                    nextId: resIds[offset],
                });
            } else {
                await this.model.load({ resId: resIds[offset] });
            }
        } catch (e) {
            if (e instanceof FetchRecordError) {
                this.model.load({
                    resIds: this.model.config.resIds.filter((id) => !e.resIds.includes(id)),
                });
            }
            throw e;
        }
    }

    beforeVisibilityChange() {
        if (document.visibilityState === "hidden" && this.formInDialog === 0) {
            return this.model.root.save();
        }
    }

    async beforeLeave() {
        if (this.model.root.dirty && !this.allowLeavingWithoutSaving) {
            return this.save({
                reload: false,
                onError: this.onSaveError.bind(this),
            });
        }
    }

    async beforeUnload(ev) {
        const succeeded = await this.model.root.urgentSave();
        if (!succeeded) {
            ev.preventDefault();
            ev.returnValue = "Unsaved changes";
        }
    }

    getStaticActionMenuItems() {
        const { activeActions } = this.archInfo;
        return {
            archive: {
                isAvailable: () => this.archiveEnabled && this.model.root.isActive,
                sequence: 10,
                description: _t("Archive"),
                icon: "oi oi-archive",
                callback: () => {
                    this.dialogService.add(ConfirmationDialog, this.archiveDialogProps);
                },
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled && !this.model.root.isActive,
                sequence: 20,
                icon: "oi oi-unarchive",
                description: _t("Unarchive"),
                callback: () => this.model.root.unarchive(),
            },
            duplicate: {
                isAvailable: () => activeActions.create && activeActions.duplicate,
                sequence: 30,
                icon: "fa fa-clone",
                description: _t("Duplicate"),
                callback: () => this.duplicateRecord(),
            },
            delete: {
                isAvailable: () => activeActions.delete && !this.model.root.isNew,
                sequence: 40,
                icon: "fa fa-trash-o",
                description: _t("Delete"),
                callback: () => this.deleteRecord(),
                skipSave: true,
            },
            addPropertyFieldValue: {
                isAvailable: () => activeActions.addPropertyFieldValue,
                sequence: 50,
                icon: "fa fa-cogs",
                description: _t("Add Properties"),
                callback: () => this.model.bus.trigger("PROPERTY_FIELD:ADD_PROPERTY_VALUE"),
            },
        };
    }

    get archiveDialogProps() {
        return {
            body: _t("Are you sure that you want to archive this record?"),
            confirmLabel: _t("Archive"),
            confirm: () => this.model.root.archive(),
            cancel: () => {},
        };
    }

    get actionMenuItems() {
        const { actionMenus } = this.props.info;
        const staticActionItems = Object.entries(this.getStaticActionMenuItems())
            .filter(([key, item]) => item.isAvailable === undefined || item.isAvailable())
            .sort(([k1, item1], [k2, item2]) => (item1.sequence || 0) - (item2.sequence || 0))
            .map(([key, item]) =>
                Object.assign({ key }, omit(item, "isAvailable", "sequence"), {
                    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
                })
            );

        return {
            action: [...staticActionItems, ...(actionMenus.action || [])],
            print: actionMenus.print,
        };
    }

    // enable the archive feature in Actions menu only if the active field is in the view
    get archiveEnabled() {
        return "active" in this.model.root.activeFields
            ? !this.props.fields.active.readonly
            : "x_active" in this.model.root.activeFields
            ? !this.props.fields.x_active.readonly
            : false;
    }

    async shouldExecuteAction(item) {
        const dirty = await this.model.root.isDirty();
        if ((dirty || this.model.root.isNew) && !item.skipSave) {
            let hasError = false;
            const isSaved = await this.model.root.save({
                onError: (...args) => {
                    hasError = true;
                    return this.onSaveError(...args);
                },
            });
            return isSaved && !hasError;
        }
        return true;
    }

    async duplicateRecord() {
        await this.model.root.duplicate();
        this.duplicateId = this.model.root.id;
    }

    get deleteConfirmationDialogProps() {
        return {
            title: _t("Bye-bye, record!"),
            body: deleteConfirmationMessage,
            confirm: async () => {
                await this.model.root.delete();
                if (!this.model.root.resId) {
                    this.env.config.historyBack();
                }
            },
            confirmLabel: _t("Delete"),
            cancel: () => {},
            cancelLabel: _t("No, keep it"),
        };
    }

    async deleteRecord() {
        this.dialogService.add(ConfirmationDialog, this.deleteConfirmationDialogProps);
    }

    async beforeExecuteActionButton(clickParams) {
        const record = this.model.root;
        if (clickParams.special !== "cancel") {
            let saved = false;
            if (clickParams.special === "save" && this.props.saveRecord) {
                saved = await this.props.saveRecord(record, clickParams);
            } else {
                const params = { reload: !(this.env.inDialog && clickParams.close) };
                saved = await record.save(params);
            }
            if (saved !== false && this.props.onSave) {
                this.props.onSave(record, clickParams);
            }
            return saved;
        } else if (this.props.onDiscard) {
            this.props.onDiscard(record);
        }
    }

    async afterExecuteActionButton(clickParams) {}

    async create() {
        const dirty = await this.model.root.isDirty();
        const onError = this.onSaveError.bind(this);
        const canProceed = !dirty || (await this.model.root.save({ onError }));
        // FIXME: disable/enable not done in onPagerUpdate
        if (canProceed) {
            await executeButtonCallback(this.ui.activeElement, () =>
                this.model.load({ resId: false })
            );
        }
    }

    async save(params) {
        const record = this.model.root;
        let saved = false;
        if (this.props.saveRecord) {
            saved = await this.props.saveRecord(record, params);
        } else {
            saved = await record.save(params);
        }
        if (saved && this.props.onSave) {
            this.props.onSave(record, params);
        }
        return saved;
    }

    saveButtonClicked(params = {}) {
        if (!("onError" in params)) {
            params.onError = this.onSaveError.bind(this);
        }
        return executeButtonCallback(this.ui.activeElement, () => this.save(params));
    }

    async discard() {
        if (this.props.discardRecord) {
            this.props.discardRecord(this.model.root);
            return;
        }
        await this.model.root.discard();
        if (this.props.onDiscard) {
            this.props.onDiscard(this.model.root);
        }
        if (this.model.root.isNew || this.env.inDialog) {
            this.env.config.historyBack();
        }
    }

    get className() {
        const result = {};
        const { size } = this.ui;
        if (size <= SIZES.XS) {
            result.o_xxs_form_view = true;
        } else if (!this.env.inDialog && size === SIZES.XXL) {
            result["o_xxl_form_view h-100"] = true;
        }
        if (this.props.className) {
            result[this.props.className] = true;
        }
        result["o_field_highlight"] = size < SIZES.SM || hasTouch();
        return result;
    }
}
