/** @odoo-module **/

import { Field } from "@web/fields/field";
import { ButtonBox } from "@web/views/form/button_box/button_box";
import { FormCompiler } from "@web/views/form/form_compiler";
import { useViewCompiler } from "@web/views/helpers/view_compiler";
import { ViewButton } from "@web/views/view_button/view_button";
import { Notebook } from "../../core/notebook/notebook";
import { InnerGroup, OuterGroup } from "@web/views/form/form_group/form_group";
import { FormLabel } from "./form_label";

const { Component, useSubEnv, useState, xml } = owl;

export class FormRenderer extends Component {
    setup() {
        const { arch, xmlDoc } = this.props.archInfo;
        this.state = useState({}); // Used by Form Compiler
        this.templateId = useViewCompiler(FormCompiler, arch, xmlDoc, {
            className: "props.class",
        });
        useSubEnv({ model: this.props.record.model });
    }

    get record() {
        return this.props.record;
    }
}

FormRenderer.template = xml`<t t-call="{{ templateId }}" />`;
FormRenderer.components = { Field, FormLabel, ButtonBox, ViewButton, Notebook, OuterGroup, InnerGroup };
