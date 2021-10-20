/** @odoo-module **/

import { registry } from "@web/core/registry";
import { XMLParser } from "@web/core/utils/xml";
import { Pager, usePager } from "@web/search/pager/pager";
import { FormRenderer } from "@web/views/form/form_renderer";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { FieldParser } from "@web/views/helpers/view_utils";
import { Layout } from "@web/views/layout";
import { RelationalModel } from "@web/views/relational_model";
import { useViewButtons } from "@web/views/view_button/hook";

const { Component } = owl;

// -----------------------------------------------------------------------------

class FormArchParser extends XMLParser {
    parse(arch, fields) {
        const xmlDoc = this.parseXML(arch);
        const fieldParser = new FieldParser(fields, "form");
        this.visitXML(xmlDoc, (node) => {
            if (node.tagName === "field") {
                fieldParser.addField(node);
            }
        });
        return {
            arch,
            activeActions: this.getActiveActions(xmlDoc),
            xmlDoc,
            fields: ["display_name", ...fieldParser.getFields()],
            relations: fieldParser.getRelations(),
        };
    }
}

// -----------------------------------------------------------------------------

class FormView extends Component {
    setup() {
        this.archInfo = new FormArchParser().parse(this.props.arch, this.props.fields);
        this.model = useModel(RelationalModel, {
            resModel: this.props.resModel,
            resId: this.props.resId,
            resIds: this.props.resIds,
            fields: this.props.fields,
            relations: this.archInfo.relations,
            activeFields: this.archInfo.fields,
            viewMode: "form",
            rootType: "record",
        });
        this.pagerProps = usePager(this.model, this.props.resId, this.props.resIds);
        const { create, edit } = this.archInfo.activeActions;

        this.canCreate = create;
        this.canEdit = edit;

        useViewButtons(this.model);
        useSetupView({
            /** TODO **/
        });
    }

    createRecord() {
        this.model.load({ resId: null });
    }
    async saveRecord() {
        this.model.root.save();
    }
}

FormView.type = "form";
FormView.display_name = "Form";
FormView.multiRecord = false;
FormView.template = `web.FormView`;
FormView.buttonTemplate = "web.FormView.Buttons";
FormView.display = { controlPanel: { ["top-right"]: false } };
FormView.components = { Layout, FormRenderer, Pager };
FormView.props = { ...standardViewProps };

registry.category("views").add("form", FormView);
