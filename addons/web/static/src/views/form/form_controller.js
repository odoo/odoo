/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeContext } from "@web/core/context";
import { useDebugCategory } from "@web/core/debug/debug_context";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { createElement } from "@web/core/utils/xml";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { useModel } from "@web/views/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { useSetupView } from "@web/views/view_hook";
import { isX2Many } from "@web/views/utils";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { SIZES } from "@web/core/ui/ui_service";

const { Component, onWillStart, useEffect, useRef, onRendered, useState, toRaw } = owl;

const viewRegistry = registry.category("views");

export async function loadSubViews(
    activeFields,
    fields,
    context,
    resModel,
    viewService,
    userService,
    isSmall
) {
    for (const fieldName in activeFields) {
        const field = fields[fieldName];
        if (!isX2Many(field)) {
            continue; // what follows only concerns x2many fields
        }
        const fieldInfo = activeFields[fieldName];
        if (fieldInfo.modifiers.invisible === true) {
            continue; // no need to fetch the sub view if the field is always invisible
        }

        if (!fieldInfo.FieldComponent.useSubView) {
            continue; // the FieldComponent used to render the field doesn't need a sub view
        }

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
        const { fields: comodelFields, relatedModels, views } = await viewService.loadViews({
            resModel: comodel,
            views: [[false, viewType]],
            context: makeContext([fieldContext, userService.context, refinedContext]),
        });
        const { ArchParser } = viewRegistry.get(viewType);
        const archInfo = new ArchParser().parse(views[viewType].arch, relatedModels, comodel);
        fieldInfo.views[viewType] = { ...archInfo, fields: comodelFields };
        fieldInfo.relatedFields = comodelFields;
    }
}

// -----------------------------------------------------------------------------

export class FormController extends Component {
    setup() {
        this.dialogService = useService("dialog");
        this.router = useService("router");
        this.user = useService("user");
        this.viewService = useService("view");
        this.ui = useService("ui");
        useBus(this.ui.bus, "resize", this.render);

        this.archInfo = this.props.archInfo;
        const activeFields = this.archInfo.activeFields;
        let resId;
        if ("resId" in this.props) {
            resId = this.props.resId; // could be false, for "create" mode
        } else {
            resId = this.props.state ? this.props.state.resId : false;
        }
        this.beforeLoadResolver = null;
        const beforeLoadProm = new Promise((r) => {
            this.beforeLoadResolver = r;
        });
        this.model = useModel(this.props.Model, {
            resModel: this.props.resModel,
            resId,
            resIds: this.props.resIds,
            fields: this.props.fields,
            activeFields,
            viewMode: "form",
            rootType: "record",
            mode: this.props.mode,
            beforeLoadProm,
        });
        const { create, edit } = this.archInfo.activeActions;

        this.canCreate = create && !this.props.preventCreate;
        this.canEdit = edit && !this.props.preventEdit;

        this.cpButtonsRef = useRef("cpButtons");

        this.display = { ...this.props.display };
        if (this.env.inDialog) {
            this.display.controlPanel = false;
        }

        useEffect(() => {
            if (!this.env.inDialog) {
                this.updateURL();
            }
        });

        // enable the archive feature in Actions menu only if the active field is in the view
        this.archiveEnabled =
            "active" in activeFields
                ? !activeFields.active.readonly
                : "x_active" in activeFields
                ? !activeFields.x_active.readonly
                : false;

        // select footers that are not in subviews and move them to another arch
        // that will be moved to the dialog's footer (if we are in a dialog)
        const footers = [...this.archInfo.xmlDoc.querySelectorAll("footer:not(field footer")];
        if (footers.length) {
            this.footerArchInfo = Object.assign({}, this.archInfo);
            this.footerArchInfo.xmlDoc = createElement("t");
            this.footerArchInfo.xmlDoc.append(...footers);
            this.footerArchInfo.arch = this.footerArchInfo.xmlDoc.outerHTML;
            this.archInfo.arch = this.archInfo.xmlDoc.outerHTML;
        }

        const beforeExecuteAction = (clickParams) => {
            if (clickParams.special !== "cancel") {
                return this.model.root.save({ stayInEdition: true });
            }
        };
        const rootRef = useRef("root");
        useViewButtons(this.model, rootRef, { beforeExecuteAction });
        useSetupView({
            rootRef,
            beforeLeave: () => {
                if (this.model.root.isDirty) {
                    return this.model.root.save({ noReload: true, stayInEdition: true });
                }
            },
            beforeUnload: () => this.beforeUnload(),
            getLocalState: () => {
                // TODO: export the whole model?
                return {
                    resId: this.model.root.resId,
                    ...this.exportTranslateAlertState(),
                };
            },
        });
        useDebugCategory("form", { component: this });

        usePager(() => {
            if (!this.model.root.isVirtual) {
                const resIds = this.model.root.resIds;
                return {
                    offset: resIds.indexOf(this.model.root.resId),
                    limit: 1,
                    total: resIds.length,
                    onUpdate: async ({ offset }) => {
                        if (this.model.root.isDirty) {
                            await this.model.root.save({ stayInEdition: true });
                        }
                        this.model.load({ resId: resIds[offset] });
                    },
                };
            }
        });

        onWillStart(async () => {
            await loadSubViews(
                this.archInfo.activeFields,
                this.props.fields,
                this.props.context,
                this.props.resModel,
                this.viewService,
                this.user,
                this.env.isSmall
            );
            this.beforeLoadResolver();
        });

        onRendered(() => {
            this.env.config.setDisplayName(this.displayName());
        });

        const { autofocusFieldId, disableAutofocus } = this.archInfo;
        if (!disableAutofocus) {
            useEffect(
                (isInEdition) => {
                    let elementToFocus;
                    if (isInEdition) {
                        elementToFocus =
                            (autofocusFieldId &&
                                rootRef.el.querySelector(`#${autofocusFieldId}`)) ||
                            rootRef.el.querySelector(".o_content .o_field_widget input");
                    } else {
                        elementToFocus =
                            rootRef.el.querySelector(".o_content button.btn-primary") ||
                            rootRef.el.querySelector(".o_control_panel .o_form_button_edit");
                    }
                    if (elementToFocus) {
                        elementToFocus.focus();
                    }
                },
                () => [this.model.root.isInEdition]
            );
        }

        this.setupTranslateAlert();
    }

    displayName() {
        return this.model.root.data.display_name || this.env._t("New");
    }

    beforeUnload() {
        return this.model.root.urgentSave();
    }

    updateURL() {
        this.router.pushState({ id: this.model.root.resId || undefined });
    }

    getActionMenuItems() {
        const otherActionItems = [];
        if (this.archiveEnabled) {
            if (this.model.root.isActive) {
                otherActionItems.push({
                    description: this.env._t("Archive"),
                    callback: () => {
                        const dialogProps = {
                            body: this.env._t(
                                "Are you sure that you want to archive all this record?"
                            ),
                            confirm: () => this.model.root.archive(),
                            cancel: () => {},
                        };
                        this.dialogService.add(ConfirmationDialog, dialogProps);
                    },
                });
            } else {
                otherActionItems.push({
                    description: this.env._t("Unarchive"),
                    callback: () => this.model.root.unarchive(),
                });
            }
        }
        if (this.archInfo.activeActions.create && this.archInfo.activeActions.duplicate) {
            otherActionItems.push({
                description: this.env._t("Duplicate"),
                callback: () => this.duplicateRecord(),
            });
        }
        if (this.archInfo.activeActions.delete) {
            otherActionItems.push({
                description: this.env._t("Delete"),
                callback: () => this.deleteRecord(),
            });
        }
        return Object.assign({}, this.props.info.actionMenus, { other: otherActionItems });
    }

    async duplicateRecord() {
        await this.model.root.duplicate();
    }

    async deleteRecord() {
        const dialogProps = {
            body: this.env._t("Are you sure you want to delete this record?"),
            confirm: async () => {
                await this.model.root.delete();
                if (!this.model.root.resId) {
                    this.env.config.historyBack();
                }
            },
            cancel: () => {},
        };
        this.dialogService.add(ConfirmationDialog, dialogProps);
    }

    disableButtons() {
        const btns = this.cpButtonsRef.el.querySelectorAll(".o_cp_buttons button");
        for (const btn of btns) {
            btn.setAttribute("disabled", "1");
        }
        return btns;
    }
    enableButtons(btns) {
        for (const btn of btns) {
            btn.removeAttribute("disabled");
        }
    }

    async edit() {
        await this.model.root.switchMode("edit");
    }

    async create() {
        this.disableButtons();
        await this.model.load({ resId: null });
    }

    async save(params = {}) {
        const disabledButtons = this.disableButtons();

        this.computeTranslateAlert();

        if (this.props.saveRecord) {
            await this.props.saveRecord(this.model.root, params);
        } else {
            await this.model.root.save();
        }
        this.enableButtons(disabledButtons);

        this.showTranslateAlert();
    }

    async discard() {
        if (this.props.discardRecord) {
            this.props.discardRecord(this.model.root);
            return;
        }
        await this.model.root.discard();
        if (this.model.root.isVirtual) {
            this.env.config.historyBack();
        }
    }

    get shouldShowTranslateAlert() {
        return localization.multiLang && this.model.root.dirtyTranslatableFields.length;
    }

    /**
     * Before we save, we gather dirty translate fields data.
     * It needs to be done before the save as nothing will be dirty after.
     * It is why there is a compute part and a show part.
     */
    computeTranslateAlert() {
        if (this.shouldShowTranslateAlert) {
            this.translateAlertData[this.model.root.resId] = new Set([
                ...(this.translateAlertData[this.model.root.resId]
                    ? toRaw(this.translateAlertData[this.model.root.resId])
                    : []),
                ...this.model.root.dirtyTranslatableFields,
            ]);
        }
    }

    /**
     * After we saved, we show the previously computed data in the alert (if there is any).
     * It needs to be done after the save because if we were in record creation, the resId
     * changed from false to a number. So it first needs to update the computed data to the new id.
     */
    showTranslateAlert() {
        if (this.translateAlertData[false]) {
            this.translateAlertData[this.model.root.resId] = this.translateAlertData[false];
            delete this.translateAlertData[false];
        }
        if (this.translateAlertData[this.model.root.resId]) {
            this.showingTranslateAlert[this.model.root.resId] = true;
        }
    }

    closeTranslateAlert() {
        this.showingTranslateAlert[this.model.root.resId] = false;
        this.translateAlertData[this.model.root.resId] = [];
    }

    /**
     * The translation alert needs to live in the scope of the action.
     * So some state may have been exported.
     * Either get the state exported data, or define new empty values.
     */
    setupTranslateAlert() {
        if (this.props.state) {
            this.showingTranslateAlert = useState(this.props.state.showingTranslateAlert || {});
            this.translateAlertData = useState(this.props.state.translateAlertData || {});
        } else {
            this.showingTranslateAlert = useState({});
            this.translateAlertData = useState({});
        }
    }

    /**
     * The translation alert needs to live in the scope of the action.
     * So some state has to be exported.
     */
    exportTranslateAlertState() {
        return {
            showingTranslateAlert: toRaw(this.showingTranslateAlert),
            translateAlertData: toRaw(this.translateAlertData),
        };
    }

    get className() {
        const { size } = this.ui;
        let sizeClass = "";
        if (size <= SIZES.XS) {
            sizeClass = "o_xxs_form_view";
        } else if (size === SIZES.XXL) {
            sizeClass = "o_xxl_form_view";
        }
        return {
            [this.props.className]: true,
            [sizeClass]: true,
        };
    }
}

FormController.template = `web.FormView`;
FormController.components = { ActionMenus, Layout };
FormController.props = {
    ...standardViewProps,
    discardRecord: { type: Function, optional: true },
    mode: {
        optional: true,
        validate: (m) => ["edit", "readonly"].includes(m),
    },
    saveRecord: { type: Function, optional: true },
    Model: Function,
    Renderer: Function,
    Compiler: Function,
    archInfo: Object,
    buttonTemplate: String,
    preventCreate: { type: Boolean, optional: true },
    preventEdit: { type: Boolean, optional: true },
};
FormController.defaultProps = {
    preventCreate: false,
    preventEdit: false,
};
