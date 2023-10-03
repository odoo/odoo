/** @odoo-module **/

import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { Notebook } from "@web/core/notebook/notebook";
import { Setting } from "./setting/setting";
import { Field } from "@web/views/fields/field";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { ButtonBox } from "@web/views/form/button_box/button_box";
import { InnerGroup, OuterGroup } from "@web/views/form/form_group/form_group";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewCompiler } from "@web/views/view_compiler";
import { useBounceButton } from "@web/views/view_hook";
import { Widget } from "@web/views/widgets/widget";
import { FormCompiler } from "./form_compiler";
import { FormLabel } from "./form_label";
import { StatusBarButtons } from "./status_bar_buttons/status_bar_buttons";

import {
    Component,
    onMounted,
    onWillUnmount,
    useEffect,
    useSubEnv,
    useRef,
    useState,
    xml,
} from "@odoo/owl";

export class FormRenderer extends Component {
    setup() {
        this.evaluateBooleanExpr = evaluateBooleanExpr;
        const { archInfo, Compiler, record } = this.props;
        const templates = { FormRenderer: archInfo.xmlDoc };
        this.state = useState({}); // Used by Form Compiler
        this.templates = useViewCompiler(Compiler || FormCompiler, templates);
        useSubEnv({ model: record.model });
        useBounceButton(useRef("compiled_view_root"), (target) => {
            return !record.isInEdition && !!target.closest(".oe_title, .o_inner_group");
        });
        this.uiService = useService("ui");
        this.onResize = useDebounced(this.render, 200);
        onMounted(() => browser.addEventListener("resize", this.onResize));
        onWillUnmount(() => browser.removeEventListener("resize", this.onResize));

        const { autofocusFieldId } = archInfo;
        if (this.shouldAutoFocus) {
            const rootRef = useRef("compiled_view_root");
            useEffect(
                (isNew, rootEl) => {
                    if (!rootEl) {
                        return;
                    }
                    let elementToFocus;
                    if (isNew) {
                        const focusableSelectors = [
                            'input[type="text"]',
                            "textarea",
                            "[contenteditable]",
                        ];
                        elementToFocus =
                            (autofocusFieldId && rootEl.querySelector(`#${autofocusFieldId}`)) ||
                            rootEl.querySelector(
                                focusableSelectors
                                    .map((sel) => `.o_content .o_field_widget ${sel}`)
                                    .join(", ")
                            );
                    }
                    if (elementToFocus) {
                        elementToFocus.focus();
                    }
                },
                () => [this.props.record.isNew, rootRef.el]
            );
        }
    }

    get shouldAutoFocus() {
        return !this.props.archInfo.disableAutofocus;
    }
}

FormRenderer.template = xml`<t t-call="{{ templates.FormRenderer }}" t-call-context="{ __comp__: Object.assign(Object.create(this), { this: this }) }" />`;
FormRenderer.components = {
    Field,
    FormLabel,
    ButtonBox,
    ViewButton,
    Widget,
    Notebook,
    Setting,
    OuterGroup,
    InnerGroup,
    StatusBarButtons,
};
FormRenderer.props = {
    archInfo: Object,
    Compiler: { type: Function, optional: true },
    record: Object,
    // Template props : added by the FormCompiler
    class: { type: String, optional: 1 },
    translateAlert: { type: [Object, { value: null }], optional: true },
    onNotebookPageChange: { type: Function, optional: true },
    activeNotebookPages: { type: Object, optional: true },
    setFieldAsDirty: { type: Function, optional: true },
};
FormRenderer.defaultProps = {
    activeNotebookPages: {},
    onNotebookPageChange: () => {},
};
