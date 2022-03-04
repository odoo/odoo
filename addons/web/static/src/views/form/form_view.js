/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeContext } from "@web/core/context";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { XMLParser } from "@web/core/utils/xml";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { usePager } from "@web/search/pager_hook";
import { FormRenderer } from "@web/views/form/form_renderer";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { getActiveActions, isX2Many } from "@web/views/helpers/view_utils";
import { Layout } from "@web/views/layout";
import { RelationalModel } from "@web/views/relational_model";
import { useViewButtons } from "@web/views/view_button/hook";
import { Field } from "@web/fields/field";

const { Component, onWillStart, useEffect, useRef, onRendered } = owl;

const viewRegistry = registry.category("views");

// -----------------------------------------------------------------------------

export class FormArchParser extends XMLParser {
    parse(arch, fields) {
        const xmlDoc = this.parseXML(arch);
        const activeActions = getActiveActions(xmlDoc);
        const activeFields = {};
        this.visitXML(xmlDoc, (node) => {
            if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, fields, "form");
                activeFields[fieldInfo.name] = fieldInfo;
                return false;
            }
        });
        return { arch, activeActions, activeFields, xmlDoc };
    }
}

// -----------------------------------------------------------------------------

export class FormView extends Component {
    setup() {
        this.dialogService = useService("dialog");
        this.router = useService("router");
        this.user = useService("user");
        this.viewService = useService("view");

        this.archInfo = new FormArchParser().parse(this.props.arch, this.props.fields);
        const activeFields = this.archInfo.activeFields;
        if (!activeFields.display_name) {
            activeFields.display_name = { name: "display_name", type: "char" };
        }
        let resId;
        if ("resId" in this.props) {
            resId = this.props.resId; // could be false, for "create" mode
        } else {
            resId = this.props.state ? this.props.state.resId : false;
        }
        this.model = useModel(RelationalModel, {
            resModel: this.props.resModel,
            resId,
            resIds: this.props.resIds,
            fields: this.props.fields,
            activeFields,
            viewMode: "form",
            rootType: "record",
        });
        const { create, edit } = this.archInfo.activeActions;

        this.canCreate = create;
        this.canEdit = edit;

        this.cpButtonsRef = useRef("cpButtons");

        useEffect(() => {
            this.router.pushState({ id: this.model.root.resId || undefined });
        });

        // enable the archive feature in Actions menu only if the active field is in the view
        this.archiveEnabled = "active" in activeFields || "x_active" in activeFields;

        useViewButtons(this.model, (clickParams) => {
            if (clickParams.special !== "cancel") {
                return this.model.root.save({ stayInEdition: true });
            }
        });
        useSetupView({
            beforeLeave: () => {
                if (this.model.root.isDirty) {
                    return this.model.root.save();
                }
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
            await this.loadSubViews();
        });

        onRendered(() => {
            this.env.config.setDisplayName(this.model.root.data.display_name || this.env._t("New"));
        });
    }

    async loadSubViews() {
        const activeFields = this.archInfo.activeFields;
        for (const fieldName in activeFields) {
            const field = this.props.fields[fieldName];
            if (!isX2Many(field)) {
                continue; // what follows only concerns x2many fields
            }
            const fieldInfo = activeFields[fieldName];
            if (fieldInfo.modifiers.invisible === true) {
                continue; // no need to fetch the sub view if the field is always invisible
            }
            if (fieldInfo.views[fieldInfo.viewMode]) {
                continue; // the sub view is inline in the main form view
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
            for (const key in this.props.context) {
                if (key.indexOf("_view_ref") === -1) {
                    refinedContext[key] = this.props.context[key];
                }
            }
            // specify the main model to prevent access rights defined in the context
            // (e.g. create: 0) to apply to sub views (same logic as the one applied by
            // the server for inline views)
            refinedContext.base_model_name = this.props.resModel;

            const viewType = fieldInfo.viewMode;
            const views = await this.viewService.loadViews({
                resModel: field.relation,
                views: [[false, viewType]],
                context: makeContext([fieldContext, this.user.context, refinedContext]),
            });
            const subView = views[viewType];
            const { ArchParser } = viewRegistry.get(viewType);
            const archInfo = new ArchParser().parse(subView.arch, subView.fields);
            fieldInfo.views[viewType] = { ...archInfo, fields: subView.fields };
            fieldInfo.relatedFields = subView.fields;
        }
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
        await this.model.root.save();
        this.enableButtons(disabledButtons);
    }
    discard() {
        this.model.root.discard();
        if (this.model.root.isVirtual) {
            this.env.config.historyBack();
        }
    }
}

FormView.type = "form";
FormView.display_name = "Form";
FormView.multiRecord = false;
FormView.template = `web.FormView`;
FormView.buttonTemplate = "web.FormView.Buttons";
FormView.display = { controlPanel: { ["top-right"]: false } };
FormView.components = { ActionMenus, FormRenderer, Layout };
FormView.props = { ...standardViewProps };
FormView.ArchParser = FormArchParser;

registry.category("views").add("form", FormView);
