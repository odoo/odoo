/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeContext } from "@web/core/context";
import { useService } from "@web/core/utils/hooks";
import { createElement } from "@web/core/utils/xml";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { isX2Many } from "@web/views/helpers/view_utils";
import { useViewButtons } from "@web/views/view_button/hook";

const { Component, onWillStart, useEffect, useRef, onRendered } = owl;

const viewRegistry = registry.category("views");

export async function loadSubViews(
    activeFields,
    fields,
    context,
    resModel,
    viewService,
    userService
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
        if (fieldInfo.views[fieldInfo.viewMode]) {
            continue; // the sub view is inline in the main form view // TODO: check this (not sure about this (DAM))
        }
        if (!fieldInfo.FieldComponent.useSubView) {
            continue; // the FieldComponent used to render the field doesn't need a sub view
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
        let viewMode = fieldInfo.viewMode;
        if (!viewMode) {
            viewMode = "list,kanban";
        } else if (viewMode === "tree") {
            viewMode = "list";
        }
        if (viewMode.indexOf(",") !== -1) {
            // WOWL do this elsewhere or get env here?
            viewMode = /** env.isSmall  ? "kanban" : */ "list";
        }
        fieldInfo.viewMode = viewMode;
        let viewType = viewMode;
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

        this.canCreate = create;
        this.canEdit = edit;

        this.cpButtonsRef = useRef("cpButtons");

        useEffect(() => {
            if (!this.env.inDialog) {
                this.router.pushState({ id: this.model.root.resId || undefined });
            }
        });

        // enable the archive feature in Actions menu only if the active field is in the view
        this.archiveEnabled =
            "active" in activeFields
                ? !activeFields.active.readonly
                : "x_active" in activeFields
                ? !activeFields.x_active.readonly
                : false;
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
            beforeUnload: () => {
                return this.model.root.urgentSave();
            },
            getLocalState: () => {
                // TODO: export the whole model?
                return { resId: this.model.root.resId };
            },
        });

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
                this.user
            );
            this.beforeLoadResolver();
        });

        onRendered(() => {
            this.env.config.setDisplayName(this.model.root.data.display_name || this.env._t("New"));
        });
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

    edit() {
        this.model.root.switchMode("edit");
    }

    async create() {
        this.disableButtons();
        await this.model.load({ resId: null });
    }

    async save() {
        const disabledButtons = this.disableButtons();
        if (this.props.saveRecord) {
            await this.props.saveRecord(this.model.root);
        } else {
            await this.model.root.save();
        }
        this.enableButtons(disabledButtons);
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
};
