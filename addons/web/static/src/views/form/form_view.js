/* @odoo-module */

import { useSetupView } from "@web/views/helpers/view_hook";
import { registry } from "../../core/registry";
import { XMLParser } from "../../core/utils/xml";
import { ControlPanel } from "../../search/control_panel/control_panel";
import { Pager, usePager } from "../../search/pager/pager";
import { useModel } from "../../views/helpers/model";
import { FieldParser } from "../helpers/view_utils";
import { RelationalModel } from "../relational_model";
import { FormRenderer } from "./form_renderer";
import { useViewButtons } from "@web/views/view_button/hook";

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
            xmlDoc,
            fields: ["display_name", ...fieldParser.getFields()],
            relations: fieldParser.getRelations(),
        };
    }
}

// -----------------------------------------------------------------------------

class FormView extends owl.Component {
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
        });
        this.pagerProps = usePager(this.model, this.props.resId, this.props.resIds);

        this.canCreate = true;
        this.canEdit = true;

        useViewButtons(this.model);

        useSetupView({
            /** TODO **/
        });
    }

    createRecord() {
        this.model.resId = null;
        this.model.load();
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
FormView.components = { ControlPanel, FormRenderer, Pager };

registry.category("views").add("form", FormView);
