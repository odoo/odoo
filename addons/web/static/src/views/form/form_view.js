/* @odoo-module */

import { registry } from "@web/core/registry";
import { XMLParser } from "@web/core/utils/xml";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { Pager, usePager } from "@web/search/pager/pager";
import { useModel } from "@web/views/helpers/model";
import { useDebugMenu } from "../../core/debug/debug_menu";
import { RelationalModel } from "../relational_model";
import { FormRenderer } from "./form_renderer";
import { useActionButtons } from "@web/views/form/view_button/hook";

// -----------------------------------------------------------------------------

class FormArchParser extends XMLParser {
    parse(arch) {
        const _fields = new Set();
        _fields.add("display_name");
        const xmlDoc = this.parseXML(arch);
        this.visitXML(xmlDoc, (node) => {
            if (node.tagName === "field") {
                _fields.add(node.getAttribute("name"));
            }
        });
        return { fields: [..._fields], arch, xmlDoc };
    }
}

// -----------------------------------------------------------------------------

class FormView extends owl.Component {
    static type = "form";
    static display_name = "Form";
    static multiRecord = false;
    static template = `web.FormView`;
    static components = { ControlPanel, FormRenderer, Pager };

    setup() {
        useDebugMenu("view", { component: this });
        this.archInfo = new FormArchParser().parse(this.props.arch);
        this.model = useModel(RelationalModel, {
            resModel: this.props.resModel,
            resId: this.props.resId,
            resIds: this.props.resIds,
            fields: this.props.fields,
            activeFields: this.archInfo.fields,
        });
        this.pagerProps = usePager(this.model, this.props.resId, this.props.resIds);

        useActionButtons(this.model);
    }
}

registry.category("views").add("form", FormView);
