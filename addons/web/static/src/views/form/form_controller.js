/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeContext } from "@web/core/context";
import { useDebugCategory } from "@web/core/debug/debug_context";
import { registry } from "@web/core/registry";
import { SIZES } from "@web/core/ui/ui_service";
import { useBus, useService } from "@web/core/utils/hooks";
import { createElement } from "@web/core/utils/xml";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { useModel } from "@web/views/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { isX2Many } from "@web/views/utils";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { useSetupView } from "@web/views/view_hook";

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

        this.beforeLoadResolver = null;
        const beforeLoadProm = new Promise((r) => {
            this.beforeLoadResolver = r;
        });
        this.model = useModel(
            this.props.Model,
            {
                resModel: this.props.resModel,
                resId: this.props.resId || false,
                resIds: this.props.resIds,
                fields: this.props.fields,
                activeFields,
                viewMode: "form",
                rootType: "record",
                mode: this.props.mode,
                beforeLoadProm,
            },
            {
                ignoreUseSampleModel: true,
            }
        );
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
                return this.model.root.save({ stayInEdition: true }).then((saved) => {
                    if (saved && this.props.onSave) {
                        this.props.onSave(this.model.root);
                    }
                    return saved;
                });
            } else if (this.props.onDiscard) {
                this.props.onDiscard(this.model.root);
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
                    fieldsToTranslate: toRaw(this.fieldsToTranslate),
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
                        const canProceed = await this.model.root.save({ stayInEdition: true });
                        if (canProceed) {
                            this.model.load({ resId: resIds[offset] });
                        }
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

        const { disableAutofocus } = this.archInfo;
        if (!disableAutofocus) {
            useEffect(
                (isInEdition) => {
                    if (
                        !isInEdition &&
                        !rootRef.el.querySelector(".o_content").contains(document.activeElement)
                    ) {
                        const elementToFocus =
                            rootRef.el.querySelector(".o_content button.btn-primary") ||
                            rootRef.el.querySelector(".o_control_panel .o_form_button_edit");
                        if (elementToFocus) {
                            elementToFocus.focus();
                        }
                    }
                },
                () => [this.model.root.isInEdition]
            );
        }

        const { fieldsToTranslate } = this.props.state || {};
        this.fieldsToTranslate = useState(fieldsToTranslate || {});
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
                    key: "archive",
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
                    key: "unarchive",
                    description: this.env._t("Unarchive"),
                    callback: () => this.model.root.unarchive(),
                });
            }
        }
        if (this.archInfo.activeActions.create && this.archInfo.activeActions.duplicate) {
            otherActionItems.push({
                key: "duplicate",
                description: this.env._t("Duplicate"),
                callback: () => this.duplicateRecord(),
            });
        }
        if (this.archInfo.activeActions.delete) {
            otherActionItems.push({
                key: "delete",
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
        const record = this.model.root;
        let saved = false;

        // Before we save, we gather dirty translate fields data. It needs to be done before the
        // save as nothing will be dirty after. It is why there is a compute part and a show part.
        if (record.dirtyTranslatableFields.length) {
            const { resId } = record;
            this.fieldsToTranslate[resId] = new Set([
                ...toRaw(this.fieldsToTranslate[resId] || []),
                ...record.dirtyTranslatableFields,
            ]);
        }

        if (this.props.saveRecord) {
            saved = await this.props.saveRecord(record, params);
        } else {
            saved = await record.save();
        }
        this.enableButtons(disabledButtons);
        if (saved && this.props.onSave) {
            this.props.onSave(record);
        }

        // After we saved, we show the previously computed data in the alert (if there is any).
        // It needs to be done after the save because if we were in record creation, the resId
        // changed from false to a number. So it first needs to update the computed data to the new id.
        if (this.fieldsToTranslate.false) {
            this.fieldsToTranslate[record.resId] = this.fieldsToTranslate.false;
            delete this.fieldsToTranslate.false;
        }
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
        if (this.model.root.isVirtual) {
            this.env.config.historyBack();
        }
    }

    get translateAlert() {
        const { resId } = this.model.root;
        if (!this.fieldsToTranslate[resId]) {
            return null;
        }

        return {
            fields: this.fieldsToTranslate[resId],
            close: () => {
                delete this.fieldsToTranslate[resId];
            },
        };
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
        return result;
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
    onDiscard: { type: Function, optional: true },
    onSave: { type: Function, optional: true },
};
FormController.defaultProps = {
    preventCreate: false,
    preventEdit: false,
};
