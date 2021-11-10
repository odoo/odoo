/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useEffect, useService } from "@web/core/utils/hooks";
import { XMLParser } from "@web/core/utils/xml";
import { usePager } from "@web/search/pager_hook";
import { FormRenderer } from "@web/views/form/form_renderer";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { processField, getActiveActions } from "@web/views/helpers/view_utils";
import { Layout } from "@web/views/layout";
import { RelationalModel } from "@web/views/relational_model";
import { useViewButtons } from "@web/views/view_button/hook";
import { ListArchParser } from "../list/list_view";
import { KanbanArchParser } from "../kanban/kanban_view";

const { Component, useState } = owl;

// -----------------------------------------------------------------------------

class FormArchParser extends XMLParser {
    parse(arch, fields) {
        const xmlDoc = this.parseXML(arch);
        const activeActions = getActiveActions(xmlDoc);
        const activeFields = {};
        this.visitXML(xmlDoc, (node) => {
            if (node.tagName === "field") {
                const fieldInfo = processField(node, fields, "form");
                const field = fields[fieldInfo.name];
                if (field.views) {
                    fieldInfo.views = {};
                    for (let viewType in field.views) {
                        const subView = field.views[viewType];
                        viewType = viewType === "tree" ? "list" : viewType; // FIXME: get rid of this
                        let Parser;
                        switch (viewType) {
                            case "form": {
                                Parser = FormArchParser;
                                break;
                            }
                            case "kanban": {
                                Parser = KanbanArchParser;
                                break;
                            }
                            case "list": {
                                Parser = ListArchParser;
                                break;
                            }
                        }
                        const archInfo = new Parser().parse(subView.arch, subView.fields);
                        fieldInfo.views[viewType] = {
                            ...archInfo,
                            activeFields: archInfo.fields,
                            fields: subView.fields,
                        };
                    }
                }
                if (!fieldInfo.invisible && ["one2many", "many2many"].includes(field.type)) {
                    fieldInfo.relation = field.relation;
                    const relatedFields = {};
                    if (fieldInfo.FieldComponent.useSubView) {
                        const firstView = fieldInfo.views && fieldInfo.views[fieldInfo.viewMode];
                        if (firstView) {
                            Object.assign(relatedFields, firstView.fields);
                        }
                    }
                    // add fields required by specific FieldComponents
                    Object.assign(relatedFields, fieldInfo.FieldComponent.fieldsToFetch);
                    // special case for color field
                    const colorField = fieldInfo.options.color_field;
                    if (colorField) {
                        relatedFields[colorField] = { name: colorField, type: "integer" };
                    }
                    fieldInfo.relatedFields = relatedFields;
                }
                activeFields[fieldInfo.name] = fieldInfo;
            }
        });
        return { arch, activeActions, fields: activeFields, xmlDoc };
    }
}

// -----------------------------------------------------------------------------

class FormView extends Component {
    setup() {
        this.router = useService("router");
        this.archInfo = new FormArchParser().parse(this.props.arch, this.props.fields);
        const activeFields = this.archInfo.fields;
        if (!activeFields.display_name) {
            activeFields.display_name = { name: "display_name", type: "char" };
        }
        const resIds = this.props.resIds || (this.props.resId ? [this.props.resId] : []);
        this.model = useModel(RelationalModel, {
            resModel: this.props.resModel,
            resId: this.props.resId,
            resIds,
            fields: this.props.fields,
            activeFields,
            viewMode: "form",
            rootType: "record",
        });
        const { create, edit } = this.archInfo.activeActions;

        this.canCreate = create;
        this.canEdit = edit;

        this.state = useState({
            inEditMode: !this.props.resId,
        });

        useEffect(() => {
            this.router.pushState({ id: this.model.root.resId || undefined });
        });

        useViewButtons(this.model);
        useSetupView({
            /** TODO **/
        });

        // FIXME: handle creation of new records (for now, indicates 0/total)
        usePager(() => {
            return {
                offset: resIds.indexOf(this.model.root.resId),
                limit: 1,
                total: resIds.length,
                onUpdate: ({ offset }) => this.model.load({ resId: this.props.resIds[offset] }),
            };
        });
    }

    /**
     * FIXME: in owl2, will use hook "onRender"
     */
    __render() {
        this.env.config.displayName = this.model.root.data.display_name || this.env._t("New");
        return super.__render(...arguments);
    }

    edit() {
        this.state.inEditMode = true;
    }
    async create() {
        await this.model.load({ resId: null });
        this.state.inEditMode = true;
    }
    async save() {
        await this.model.root.save();
        this.state.inEditMode = false;
    }
    discard() {
        this.model.root.discard();
        if (this.model.root.resId) {
            this.state.inEditMode = false;
        } else {
            this.trigger("history-back");
        }
    }
}

FormView.type = "form";
FormView.display_name = "Form";
FormView.multiRecord = false;
FormView.template = `web.FormView`;
FormView.buttonTemplate = "web.FormView.Buttons";
FormView.display = { controlPanel: { ["top-right"]: false } };
FormView.components = { Layout, FormRenderer };
FormView.props = { ...standardViewProps };

registry.category("views").add("form", FormView);
