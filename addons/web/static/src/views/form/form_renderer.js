/** @odoo-module **/

import { Field } from "@web/fields/field";
import { ButtonBox } from "@web/views/form/button_box/button_box";
import { FormCompiler } from "@web/views/form/form_compiler";
import { useViewCompiler } from "@web/views/helpers/view_compiler";
import { ViewButton } from "@web/views/view_button/view_button";

const { Component, useSubEnv, useState, useEffect, xml } = owl;

export class FormRenderer extends Component {
    setup() {
        const { arch, activeFields, xmlDoc } = this.props.archInfo;
        this.state = useState({}); // Used by Form Compiler
        this.templateId = useViewCompiler(FormCompiler, arch, activeFields, xmlDoc);
        useSubEnv({ model: this.props.record.model });
        useEffect(() => {
            if (this.props.class) {
                // should be done differently
                this.el.classList.add(...this.props.class.split(/\s+/g));
            }
        });
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
