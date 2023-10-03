/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { hasTouch } from "@web/core/browser/feature_detection";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeContext } from "@web/core/context";
import { useDebugCategory } from "@web/core/debug/debug_context";
import { registry } from "@web/core/registry";
import { SIZES } from "@web/core/ui/ui_service";
import { useBus, useService } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";
import { createElement, parseXML } from "@web/core/utils/xml";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { standardViewProps } from "@web/views/standard_view_props";
import { isX2Many } from "@web/views/utils";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { useSetupView } from "@web/views/view_hook";
import { ViewButton } from "@web/views/view_button/view_button";
import { Field } from "@web/views/fields/field";
import { useModel } from "@web/model/model";
import { addFieldDependencies, extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { useViewCompiler } from "@web/views/view_compiler";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

import { ButtonBox } from "./button_box/button_box";
import { FormCompiler } from "./form_compiler";
import { FormErrorDialog } from "./form_error_dialog/form_error_dialog";
import { FormStatusIndicator } from "./form_status_indicator/form_status_indicator";

import { Component, onRendered, useEffect, useRef, useState } from "@odoo/owl";

const viewRegistry = registry.category("views");

export async function loadSubViews(
    fieldNodes,
    fields,
    context,
    resModel,
    viewService,
    userService,
    isSmall
) {
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
        viewType = viewType.replace("tree", "list");
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
        // specify the main model to prevent access rights defined in the context
        // (e.g. create: 0) to apply to sub views (same logic as the one applied by
        // the server for inline views)
        refinedContext.base_model_name = resModel;

        const comodel = field.relation;
        const {
            fields: comodelFields,
            relatedModels,
            views,
        } = await viewService.loadViews({
            resModel: comodel,
            views: [[false, viewType]],
            context: makeContext([fieldContext, userService.context, refinedContext]),
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

// -----------------------------------------------------------------------------

export class FormController extends Component {
    setup() {
        this.evaluateBooleanExpr = evaluateBooleanExpr;
        this.dialogService = useService("dialog");
        this.router = useService("router");
        this.orm = useService("orm");
        this.user = useService("user");
        this.viewService = useService("view");
        this.ui = useService("ui");
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

        const beforeFirstLoad = async () => {
            await loadSubViews(
                this.archInfo.fieldNodes,
                this.props.fields,
                this.props.context,
                this.props.resModel,
                this.viewService,
                this.user,
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

        this.cpButtonsRef = useRef("cpButtons");

        useEffect(() => {
            if (!this.env.inDialog) {
                this.updateURL();
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

        const xmlDocButtonBox = this.archInfo.xmlDoc.querySelector("div[name='button_box']");
        if (xmlDocButtonBox) {
            const buttonBoxTemplates = useViewCompiler(
                this.props.Compiler || FormCompiler,
                { ButtonBox: xmlDocButtonBox },
                { isSubView: true }
            );
            this.buttonBoxTemplate = buttonBoxTemplates.ButtonBox;
        }

        this.rootRef = useRef("root");
        useViewButtons(this.model, this.rootRef, {
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
        });

        const state = this.props.state || {};
        const activeNotebookPages = { ...state.activeNotebookPages };
        this.onNotebookPageChange = (notebookId, page) => {
            if (page) {
                activeNotebookPages[notebookId] = page;
            }
        };

        useSetupView({
            rootRef: this.rootRef,
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
                onDiscard: () => {
                    discard();
                    resolve(true);
                },
                onStayHere: () => resolve(false),
            });
        });
        return proceed;
    }

    displayName() {
        return this.model.root.data.display_name || _t("New");
    }

    async onPagerUpdate({ offset, resIds }) {
        const dirty = await this.model.root.isDirty();
        if (dirty) {
            return this.model.root.save({
                onError: this.onSaveError.bind(this),
                nextId: resIds[offset],
            });
        } else {
            return this.model.load({ resId: resIds[offset] });
        }
    }

    async beforeLeave() {
        if (this.model.root.dirty) {
            return this.model.root.save({
                reload: false,
                onError: this.onSaveError.bind(this),
            });
        }
    }

    async beforeUnload(ev) {
        const isValid = await this.model.root.urgentSave();
        if (!isValid) {
            ev.preventDefault();
            ev.returnValue = "Unsaved changes";
        }
    }

    updateURL() {
        this.router.pushState({ id: this.model.root.resId || undefined });
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
            body: _t("Are you sure you want to delete this record?"),
            confirm: async () => {
                await this.model.root.delete();
                if (!this.model.root.resId) {
                    this.env.config.historyBack();
                }
            },
            confirmLabel: _t("Delete"),
            cancel: () => {},
        };
    }

    async deleteRecord() {
        this.dialogService.add(ConfirmationDialog, this.deleteConfirmationDialogProps);
    }

    disableButtons() {
        const btns = [...this.ui.activeElement.querySelectorAll("button:not([disabled])")];
        for (const btn of btns) {
            btn.setAttribute("disabled", "");
        }
        return btns;
    }

    enableButtons(btns) {
        for (const btn of btns) {
            btn.removeAttribute("disabled");
        }
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
        const canProceed = await this.model.root.save({
            onError: this.onSaveError.bind(this),
        });
        // FIXME: disable/enable not done in onPagerUpdate
        if (canProceed) {
            const btns = this.disableButtons();
            await this.model.load({ resId: false });
            this.enableButtons(btns);
        }
    }

    async saveButtonClicked(params = {}) {
        const btns = this.disableButtons();
        const record = this.model.root;
        let saved = false;
        try {
            if (this.props.saveRecord) {
                saved = await this.props.saveRecord(record, params);
            } else {
                saved = await record.save(params);
            }
        } finally {
            this.enableButtons(btns);
        }
        if (saved && this.props.onSave) {
            this.props.onSave(record, params);
        }
        return saved;
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

FormController.template = `web.FormView`;
FormController.components = {
    FormStatusIndicator,
    Layout,
    ButtonBox,
    ViewButton,
    Field,
    CogMenu,
};
FormController.props = {
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
FormController.defaultProps = {
    preventCreate: false,
    preventEdit: false,
};
