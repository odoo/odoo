/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useEffect, useService } from "@web/core/utils/hooks";
import { XMLParser } from "@web/core/utils/xml";
import { usePager } from "@web/search/pager_hook";
import { FormRenderer } from "@web/views/form/form_renderer";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { getActiveActions } from "@web/views/helpers/view_utils";
import { Layout } from "@web/views/layout";
import { RelationalModel } from "@web/views/relational_model";
import { useViewButtons } from "@web/views/view_button/hook";
import { Field } from "@web/fields/field";

const { Component, useState } = owl;

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
        let resId;
        if ("resId" in this.props) {
            resId = this.props.resId; // could be false, for "create" mode
        } else {
            resId = this.props.state ? this.props.state.resId : false;
        }
        this.model = useModel(RelationalModel, {
            resModel: this.props.resModel,
            resId,
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
            inEditMode: !resId,
        });

        useEffect(() => {
            this.router.pushState({ id: this.model.root.resId || undefined });
        });

        useViewButtons(this.model);
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
        this.env.config.setDisplayName(this.model.root.data.display_name || this.env._t("New"));
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
FormView.ArchParser = FormArchParser;

registry.category("views").add("form", FormView);
