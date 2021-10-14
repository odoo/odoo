/** @odoo-module **/

import { Field } from "@web/fields/field";
import { useFormCompiler } from "@web/views/form/form_compiler";
import { ViewButton } from "@web/views/view_button/view_button";
import { ButtonBox } from "./button_box/button_box";

const { Component, hooks, tags } = owl;
const { useSubEnv, useState } = hooks;
const { xml } = tags;

export class FormRenderer extends Component {
    setup() {
        const { arch, fields, xmlDoc } = this.props.info;
        this.owlifiedArch = useFormCompiler(arch, fields, xmlDoc);
        this.state = useState({});
        if (!this.env.model) {
            useSubEnv({ model: this.props.record.model });
        }
    }

    get record() {
        return this.props.record;
    }

    getActivePage(record, invisibleDomains) {
        for (const page in invisibleDomains) {
            if (!invisibleDomains[page] || !this.evalDomain(record, invisibleDomains[page])) {
                return page;
            }
        }
    }
}

FormRenderer.template = xml`<t t-call="{{ owlifiedArch }}" />`;
FormRenderer.components = { Field, ButtonBox, ViewButton };
