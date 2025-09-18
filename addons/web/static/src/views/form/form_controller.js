// @ts-check

/** @module @web/views/form/form_controller - Form view lifecycle: record save, discard, duplicate, archive, pager navigation, and error recovery */

import {
    Component,
    onError,
    onMounted,
    onRendered,
    status,
    useEffect,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { hasTouch } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { createElement } from "@web/core/utils/dom/xml";
import { useBus, useService } from "@web/core/utils/hooks";
import { effect } from "@web/core/utils/reactive";
import { Field } from "@web/fields/field";
import { useModel } from "@web/model/model";
import { FetchRecordError } from "@web/model/relational_model/errors";
import {
    addFieldDependencies,
    extractFieldsFromArchInfo,
} from "@web/model/relational_model/utils";
import { useSetupAction } from "@web/search/action_hook";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { useDebugCategory } from "@web/services/debug/debug_context";
import { user } from "@web/services/user";
import { SIZES } from "@web/ui/block/ui_service";
import { ConfirmationDialog } from "@web/ui/dialog/confirmation_dialog";
import { standardViewProps } from "@web/views/standard_view_props";
import { ViewButton } from "@web/views/view_button/view_button";
import {
    executeButtonCallback,
    useViewButtons,
} from "@web/views/view_button/view_button_hook";
import { useViewCompiler } from "@web/views/view_compiler";
import { useDeleteRecords } from "@web/views/view_hook";
import { buildActionMenuItems, useControllerServices } from "@web/views/view_utils";
import { Widget } from "@web/views/widgets/widget";

import { ButtonBox } from "./button_box/button_box";
import { FormCogMenu } from "./form_cog_menu/form_cog_menu";
import { FormCompiler } from "./form_compiler";
import { FormErrorDialog } from "./form_error_dialog/form_error_dialog";
import { FormStatusIndicator } from "./form_status_indicator/form_status_indicator";
import { loadSubViews, useFormViewInDialog } from "./form_utils";

/**
 * Controller for the form view.
 *
 * Manages a single record: loading, saving, discarding, duplicating, archiving,
 * deleting, pager navigation, and error recovery (including company-switching
 * on AccessError). Sub-views for x2many fields are loaded on first render.
 */
export class FormController extends Component {
    static template = `web.FormView`;
    static components = {
        FormStatusIndicator,
        Layout,
        ButtonBox,
        ViewButton,
        Field,
        CogMenu: FormCogMenu,
        Widget,
    };

    static props = {
        ...standardViewProps,
        discardRecord: { type: Function, optional: true },
        readonly: { type: Boolean, optional: true },
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
        const { action, dialog, notification, orm, uiHooks } = useControllerServices();
        this.actionService = action;
        this.dialogService = dialog;
        this.notification = notification;
        this.orm = orm;
        this._uiHooks = uiHooks;
        this.viewService = useService("view");
        this.ui = useService("ui");
        useBus(this.ui.bus, "resize", /** @type {any} */ (this.render));

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
        useBus(
            this.env.bus,
            "FORM-CONTROLLER:FORM-IN-DIALOG:ADD",
            () => this.formInDialog++,
        );
        useBus(
            this.env.bus,
            "FORM-CONTROLLER:FORM-IN-DIALOG:REMOVE",
            () => this.formInDialog--,
        );

        // Wait to be mounted before displaying dialog/notification for onchange warnings returned
        // by the first onchange, for 2 reasons:
        //  1) we don't want to show twice the warning if the component is destroyed before being
        //     mounted and re-created
        //  2) for form views in dialogs, this causes an infinite loop if willStart calls dialog.add
        const mountedProm = new Promise((r) => onMounted(/** @type {any} */ (r)));
        this.onWillDisplayOnchangeWarning = () => mountedProm;

        const beforeFirstLoad = async () => {
            await loadSubViews(
                this.archInfo.fieldNodes,
                this.props.fields,
                this.props.context,
                this.props.resModel,
                this.viewService,
                this.env.isSmall,
            );
            const { activeFields, fields } = extractFieldsFromArchInfo(
                this.archInfo,
                this.props.fields,
            );
            if (this.display.controlPanel) {
                addFieldDependencies(activeFields, fields, [
                    { name: "display_name", type: "char", readonly: true },
                ]);
            }
            this.model.config.activeFields = activeFields;
            this.model.config.fields = fields;
        };
        this.model = useState(
            useModel(this.props.Model, this.modelParams, { beforeFirstLoad }),
        );
        useSubEnv({ model: this.model });
        onMounted(() => {
            effect(
                (model) => {
                    if (status(this) === "mounted") {
                        this.props.updateActionState({
                            resId: model.root.resId,
                        });
                    }
                },
                [this.model],
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
                const activeCompanyIds = user.activeCompanies.map((c) => c.id);
                activeCompanyIds.push(suggestedCompany.id);
                user.activateCompanies(activeCompanyIds);
            } else {
                throw error;
            }
        });

        // select footers that are not in subviews and move them to another arch
        // that will be moved to the dialog's footer (if we are in a dialog)
        const footers = [
            ...this.archInfo.xmlDoc.querySelectorAll("footer:not(field footer)"),
        ];
        if (footers.length) {
            this.footerArchInfo = { ...this.archInfo };
            this.footerArchInfo.xmlDoc = createElement("t");
            this.footerArchInfo.xmlDoc.append(...footers);
            this.footerArchInfo.arch = this.footerArchInfo.xmlDoc.outerHTML;
            this.archInfo.arch = this.archInfo.xmlDoc.outerHTML;
        }

        const xmlDocButtonBox = this.archInfo.xmlDoc.querySelector(
            "div[name='button_box']:not(field div)",
        );
        if (xmlDocButtonBox) {
            const buttonBoxTemplates = useViewCompiler(
                this.props.Compiler || FormCompiler,
                { ButtonBox: xmlDocButtonBox },
                { isSubView: true },
            );
            this.buttonBoxTemplate = buttonBoxTemplates.ButtonBox;
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
            beforeLeave: (options) => this.beforeLeave(options),
            beforeUnload: (ev) => this.beforeUnload(ev),
            getLocalState: () => ({
                activeNotebookPages: !this.model.root.isNew ? activeNotebookPages : {},
                modelState: /** @type {any} */ (this.model).exportState(),
                resId: this.model.root.resId,
            }),
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
                            ".o_content button.btn-primary",
                        );
                        if (elementToFocus) {
                            elementToFocus.focus();
                        }
                    }
                },
                () => [this.model.root.isInEdition],
            );
        }

        if (this.env.inDialog) {
            useFormViewInDialog();
        }

        this.deleteRecordsWithConfirmation = useDeleteRecords(this.model);
    }

    get cogMenuProps() {
        return {
            getActiveIds: () => (this.model.root.isNew ? [] : [this.model.root.resId]),
            context: this.model.root.context,
            items: this.props.info.actionMenus ? this.actionMenuItems : {},
            isDomainSelected: this.model.root.isDomainSelected,
            resModel: this.model.root.resModel,
            domain: this.props.domain,
            onActionExecuted: ({ noReload } = /** @type {any} */ ({})) => {
                if (!noReload) {
                    const { resId, resIds } = this.model.root;
                    return this.model.load({ resId: resId, resIds: resIds });
                }
            },
            shouldExecuteAction: this.shouldExecuteAction.bind(this),
        };
    }

    get modelParams() {
        return {
            config: {
                resModel: this.props.resModel,
                resId: this.props.resId || false,
                resIds:
                    this.props.resIds || (this.props.resId ? [this.props.resId] : []),
                fields: this.props.fields,
                activeFields: {}, // will be generated after loading sub views (see willStart)
                isMonoRecord: true,
                mode: this.props.readonly ? "readonly" : "edit",
                context: this.props.context,
            },
            state: this.props.state?.modelState,
            hooks: {
                ...this._uiHooks,
                onWillLoadRoot: this.onWillLoadRoot.bind(this),
                onWillSaveRecord: this.onWillSaveRecord.bind(this),
                onRecordSaved: this.onRecordSaved.bind(this),
                onWillDisplayOnchangeWarning:
                    this.onWillDisplayOnchangeWarning.bind(this),
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
     * @param {any} record
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
                await this.orm.call(
                    this.model.root.resModel,
                    "web_override_translations",
                    [[this.model.root.resId], translationChanges],
                );
            }
        }
    }

    /**
     * onWillSaveRecord is a callback that will be executed before the
     * record save if the record is valid.
     * If it returns false, it will prevent the save.
     */
    async onWillSaveRecord() {}

    /**
     * Handle save errors. Shows a FormErrorDialog when leaving, or re-throws
     * the error otherwise. Handles AccessError with suggested_company by
     * activating the missing company and retrying.
     *
     * @param {Object} error - the RPC error
     * @param {{ discard: Function, retry: Function }} callbacks
     * @param {boolean} leaving - whether the user is navigating away
     * @returns {Promise<boolean>} whether to proceed with leaving
     */
    async onSaveError(error, { discard, retry }, leaving) {
        const suggestedCompany = error.data?.context?.suggested_company;
        const activeCompanyIds = user.activeCompanies.map((c) => c.id);
        if (
            error.data?.name === "odoo.exceptions.AccessError" &&
            suggestedCompany &&
            !activeCompanyIds.includes(suggestedCompany.id)
        ) {
            // update the context with the needed company
            this.model.config.context.allowed_company_ids.push(suggestedCompany.id);
            // activate the company without reloading !
            activeCompanyIds.push(suggestedCompany.id);
            user.activateCompanies(activeCompanyIds, { reload: false });
            return retry();
        }
        if (leaving) {
            const proceed = await new Promise((resolve) => {
                this.dialogService.add(FormErrorDialog, {
                    message: error.data.message,
                    data: error.data,
                    onDiscard: () => {
                        discard();
                        resolve(true);
                    },
                    onRedirect: async ({ action, additionalContext }) => {
                        try {
                            await this.actionService.doAction(action, {
                                additionalContext,
                                forceLeave: true,
                            });
                        } finally {
                            resolve(false);
                        }
                    },
                    onStayHere: () => resolve(false),
                });
            });
            return proceed;
        }
        throw error;
    }

    /** @returns {string} the display name for the breadcrumb (record name or "New") */
    displayName() {
        const displayName = this.model.root.data.display_name;
        if (displayName) {
            return displayName;
        }
        return (this.model.root.isNew && _t("New")) || "";
    }

    /**
     * Navigate to a different record via the pager. Saves dirty records first.
     *
     * @param {{ offset: number, resIds: number[] }} params
     */
    async onPagerUpdate({ offset, resIds }) {
        const dirty = await this.model.root.isDirty();
        try {
            if (dirty) {
                await this.model.root.save({
                    onError: (error, options) => this.onSaveError(error, options, true),
                    nextId: resIds[offset],
                });
            } else {
                await this.model.load({ resId: resIds[offset] });
            }
        } catch (e) {
            if (e instanceof FetchRecordError) {
                this.model.load({
                    resIds: this.model.config.resIds.filter(
                        (id) => !e.resIds.includes(id),
                    ),
                });
            }
            throw e;
        }
    }

    beforeVisibilityChange() {
        if (document.visibilityState === "hidden" && this.formInDialog === 0) {
            return this.model.root.save().catch(() => {});
        }
    }

    async beforeLeave({ forceLeave } = /** @type {any} */ ({})) {
        if (this.model.root.dirty && !forceLeave) {
            return this.save({
                reload: false,
                onError: (error, options) => this.onSaveError(error, options, true),
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
            addPropertyFieldValue: {
                isAvailable: () => activeActions.addPropertyFieldValue,
                sequence: 10,
                icon: "fa fa-cogs",
                description: _t("Edit Properties"),
                callback: () => this.model.bus.trigger("PROPERTY_FIELD:EDIT"),
            },
            duplicate: {
                isAvailable: () => activeActions.create && activeActions.duplicate,
                sequence: 30,
                icon: "fa fa-clone",
                description: _t("Duplicate"),
                callback: () => this.duplicateRecord(),
            },
            archive: {
                isAvailable: () => this.archiveEnabled && this.model.root.isActive,
                sequence: 40,
                description: _t("Archive"),
                icon: "oi oi-archive",
                callback: () => {
                    this.dialogService.add(ConfirmationDialog, this.archiveDialogProps);
                },
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled && !this.model.root.isActive,
                sequence: 45,
                icon: "oi oi-unarchive",
                description: _t("Unarchive"),
                callback: () => this.model.root.unarchive(),
            },
            delete: {
                isAvailable: () => activeActions.delete && !this.model.root.isNew,
                sequence: 50,
                icon: "fa fa-trash-o",
                description: _t("Delete"),
                class: "text-danger",
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
        return buildActionMenuItems(
            this.getStaticActionMenuItems(),
            this.props.info.actionMenus,
        );
    }

    // enable the archive feature in Actions menu only if the active field is in the view
    get archiveEnabled() {
        const activeFields = this.model.root.activeFields;
        if ("active" in activeFields) {
            return !this.props.fields.active.readonly;
        }
        if ("x_active" in activeFields) {
            return !this.props.fields.x_active.readonly;
        }
        return false;
    }

    async shouldExecuteAction(item) {
        const dirty = await this.model.root.isDirty();
        if ((dirty || this.model.root.isNew) && !item.skipSave) {
            let hasError = false;
            const isSaved = await this.model.root.save({
                onError: (error, options) => {
                    hasError = true;
                    return this.onSaveError(error, options, true);
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
            confirm: async () => {
                await this.model.root.delete();
                if (!this.model.root.resId) {
                    this.env.config.historyBack();
                }
            },
        };
    }

    async deleteRecord() {
        this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps, [
            this.model.root,
        ]);
    }

    async beforeExecuteActionButton(clickParams) {
        const record = this.model.root;
        if (clickParams.special !== "cancel") {
            let saved;
            if (clickParams.special === "save" && this.props.saveRecord) {
                saved = await this.props.saveRecord(record, clickParams);
            } else {
                const params = {
                    reload: !(this.env.inDialog && clickParams.close),
                };
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
        const onError = (error, options) => this.onSaveError(error, options, true);
        const canProceed = !dirty || (await this.model.root.save({ onError }));
        // FIXME: disable/enable not done in onPagerUpdate
        if (canProceed) {
            await executeButtonCallback(this.ui.activeElement, () =>
                this.model.load({ resId: false }),
            );
        }
    }

    /**
     * Save the current record. Delegates to `props.saveRecord` if provided,
     * otherwise calls `record.save()` directly.
     *
     * @param {Object} [params] - save options (e.g. { reload: false })
     * @returns {Promise<boolean>} whether the save succeeded
     */
    async save(params) {
        const record = this.model.root;
        let saved;
        if (this.props.saveRecord) {
            saved = await this.props.saveRecord(record, params);
        } else {
            saved = await record.save({
                onError: (error, options) => this.onSaveError(error, options, false),
                ...params,
            });
        }
        if (saved && this.props.onSave) {
            this.props.onSave(record, params);
        }
        return saved;
    }

    saveButtonClicked(params = {}) {
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
        if (this.env.inDialog) {
            await this.env.dialogData.close();
        } else if (this.model.root.isNew) {
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
