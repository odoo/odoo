/** @odoo-module **/

import { Field } from "@web/fields/field";
import { ButtonBox } from "@web/views/form/button_box/button_box";
import { FormCompiler } from "@web/views/form/form_compiler";
import { useViewCompiler } from "@web/views/helpers/view_compiler";
import { ViewButton } from "@web/views/view_button/view_button";

const { Component, hooks, tags } = owl;
const { useSubEnv, useState } = hooks;
const { xml } = tags;

export class FormRenderer extends Component {
    setup() {
        const { arch, fields, xmlDoc } = this.props.info;
        this.state = useState({}); // Used by Form Compiler
        this.templateId = useViewCompiler(FormCompiler, arch, fields, xmlDoc);
        useSubEnv({ model: this.props.record.model });
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

FormRenderer.template = xml`<t t-call="{{ templateId }}" />`;
FormRenderer.components = { Field, ButtonBox, ViewButton };
