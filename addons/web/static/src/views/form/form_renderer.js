/** @odoo-module **/

import { Field } from "@web/fields/field";
import { ButtonBox } from "@web/views/form/button_box/button_box";
import { InnerGroup, OuterGroup } from "@web/views/form/form_group/form_group";
import { useViewCompiler } from "@web/views/helpers/view_compiler";
import { useBounceButton } from "@web/views/helpers/view_hook";
import { ViewButton } from "@web/views/view_button/view_button";
import { ViewWidget } from "@web/views/view_widget";
import { Notebook } from "../../core/notebook/notebook";
import { FormCompiler } from "./form_compiler";
import { FormLabel } from "./form_label";

const { Component, useSubEnv, useRef, useState, xml } = owl;

export class FormRenderer extends Component {
    setup() {
        const { arch, xmlDoc } = this.props.archInfo;
        this.state = useState({}); // Used by Form Compiler
        this.templateId = useViewCompiler(this.props.Compiler || FormCompiler, arch, xmlDoc, {
            className: "props.class",
            ...this.compileParams,
        });
        useSubEnv({ model: this.props.record.model });
        useBounceButton(useRef("compiled_view_root"), () => {
            return !this.props.record.isInEdition;
        });
    }

    get record() {
        return this.props.record;
    }
}

FormRenderer.template = xml`<t t-call="{{ templateId }}" />`;
FormRenderer.components = {
    Field,
    FormLabel,
    ButtonBox,
    ViewButton,
    ViewWidget,
    Notebook,
    OuterGroup,
    InnerGroup,
};
