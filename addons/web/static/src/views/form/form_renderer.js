import { render, useLayoutEffect, useRef, useSubEnv } from "@web/owl2/utils";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { Notebook } from "@web/core/notebook/notebook";
import { Setting } from "./setting/setting";
import { Field } from "@web/views/fields/field";
import { browser } from "@web/core/browser/browser";
import { hasTouch } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";
import { useDebounced, useThrottleForAnimation } from "@web/core/utils/timing";
import { ButtonBox } from "@web/views/form/button_box/button_box";
import { InnerGroup, OuterGroup } from "@web/views/form/form_group/form_group";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewCompiler } from "@web/views/view_compiler";
import { Widget } from "@web/views/widgets/widget";
import { FormCompiler } from "./form_compiler";
import { FormLabel } from "./form_label";
import { StatusBarButtons } from "./status_bar_buttons/status_bar_buttons";

import { Component, onMounted, onWillUnmount, props, t, xml, proxy } from "@odoo/owl";

export const formRendererProps = {
    archInfo: t.object(),
    Compiler: t.function().optional(),
    record: t.object(),
    // Template props : added by the FormCompiler
    class: t.string().optional(),
    translateAlert: t.or([t.object(), t.literal(null)]).optional(),
    onNotebookPageChange: t.function().optional(() => () => {}),
    activeNotebookPages: t.object().optional({}),
    readonly: t.boolean().optional(),
    saveRecord: t.function().optional(),
    setFieldAsDirty: t.function().optional(),
};

export class FormRenderer extends Component {
    static template = xml`<t t-call="{{ this.templates.FormRenderer }}" t-call-context="{ __comp__: Object.assign(Object.create(this), { this: this }) }" />`;
    static components = {
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
    props = props(formRendererProps);

    setup() {
        this.evaluateBooleanExpr = evaluateBooleanExpr;
        const { archInfo, Compiler, record } = this.props;
        const templates = { FormRenderer: archInfo.xmlDoc };
        this.state = proxy({}); // Used by Form Compiler
        this.templates = useViewCompiler(Compiler || FormCompiler, templates);
        useSubEnv({ model: record.model });
        this.uiService = useService("ui");
        this.onResize = useDebounced(() => render(this), 200);
        this.onScrollThrottled = useThrottleForAnimation(this.onScroll);
        onMounted(() => browser.addEventListener("resize", this.onResize));
        onWillUnmount(() => browser.removeEventListener("resize", this.onResize));

        const { autofocusFieldIds } = archInfo;
        const rootRef = useRef("compiled_view_root");
        if (this.shouldAutoFocus) {
            useLayoutEffect(
                (record, rootEl) => {
                    if (!rootEl) {
                        return;
                    }
                    let elementToFocus;
                    if (record.isNew) {
                        const focusableSelectors = [
                            'input[type="text"]',
                            "textarea",
                            "[contenteditable]",
                        ];
                        for (const id of autofocusFieldIds) {
                            elementToFocus = rootEl.querySelector(`#${id}`);
                            if (elementToFocus) {
                                break;
                            }
                        }
                        elementToFocus =
                            elementToFocus ||
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
                () => [this.props.record, rootRef.el]
            );
        }

        if (this.env.inDialog) {
            // try to ensure ids unicity by temporarily removing similar ids that could already
            // exist in the DOM (e.g. in a form view displayed below this dialog which contains
            // same field names as this form view)
            const fieldNodeIds = Object.keys(this.props.archInfo.fieldNodes);
            const elementsByNodeIds = {};
            onMounted(() => {
                if (!rootRef.el) {
                    // t-ref is sometimes set on a <t> node, resulting in a null ref (e.g. footer case)
                    return;
                }
                for (const id of fieldNodeIds) {
                    const els = [...document.querySelectorAll(`[id=${id}]`)].filter(
                        (el) => !rootRef.el.contains(el)
                    );
                    if (els.length) {
                        els[0].removeAttribute("id");
                        elementsByNodeIds[id] = els[0];
                    }
                }
            });
            onWillUnmount(() => {
                for (const [id, el] of Object.entries(elementsByNodeIds)) {
                    el.setAttribute("id", id);
                }
            });
        }
    }

    get shouldAutoFocus() {
        return !hasTouch() && !this.props.archInfo.disableAutofocus;
    }

    onScroll(ev) {
        this.state.isStatusbarStickyPinned =
            !this.env.inDialog && !this.env.isSmall && ev.target.scrollTop !== 0;
    }

    async onWillChangeNotebookPage() {
        // Hack to force _askChanges
        await this.props.record.isDirty();
        return true;
    }
}
