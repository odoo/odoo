// @ts-check
/** @odoo-module native */

import {
    Component,
    onMounted,
    onWillUnmount,
    useEffect,
    useRef,
    useState,
    useSubEnv,
    xml,
} from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { Notebook } from "@web/components/notebook/notebook";
import { hasTouch } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { AppEvent } from "@web/core/events";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { mutate } from "@web/core/utils/dom/layout_batch";
import { useBus, useService } from "@web/core/utils/hooks";
import { useRenderCounter } from "@web/core/utils/render_instrumentation";
import { Field } from "@web/fields/field";
import { Dialog } from "@web/ui/dialog/dialog";
import { ButtonBox } from "@web/views/form/button_box/button_box";
import { InnerGroup, OuterGroup } from "@web/views/form/form_group/form_group";
import { ViewButton } from "@web/views/view_button/view_button";
import { compileViewTemplates } from "@web/views/view_compiler";
import { Widget } from "@web/views/widgets/widget";

import { useFieldIsDirty } from "./field_is_dirty_hook.js";
import { FormCompiler } from "./form_compiler.js";
import { FormLabel } from "./form_label.js";
import { Setting } from "./setting/setting.js";
import { StatusBarButtons } from "./status_bar_buttons/status_bar_buttons.js";

const log = makeLogger("web.view.form");

export class FormRenderer extends Component {
    static template = xml`<t t-call="{{ templates.FormRenderer }}" t-call-context="{ __comp__: Object.assign(Object.create(this), { this: this }) }" />`;
    static components = {
        Dialog,
        Dropdown,
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
    static props = {
        archInfo: Object,
        Compiler: { type: Function, optional: true },
        record: Object,
        class: { type: String, optional: 1 },
        onNotebookPageChange: { type: Function, optional: true },
        activeNotebookPages: { type: Object, optional: true },
        readonly: { type: Boolean, optional: true },
        saveRecord: { type: Function, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        activeNotebookPages: {},
        onNotebookPageChange: () => {},
    };

    /** @type {import("services").ServiceFactories["ui"]} */
    uiService;

    setup() {
        useRenderCounter("form.FormRenderer");
        useLifecycleLog(log);
        this.evaluateBooleanExpr = evaluateBooleanExpr;
        const { archInfo, Compiler, record } = this.props;
        const templates = { FormRenderer: archInfo.xmlDoc };
        this.state = useState(/** @type {any} */ ({}));
        this.archDialogs = useState(/** @type {Record<string, boolean>} */ ({}));
        this.templates = compileViewTemplates(Compiler || FormCompiler, templates);
        this.hasUnsavedEdits = useFieldIsDirty(record.model);
        useSubEnv({ model: record.model });
        this.uiService = useService("ui");
        useBus(this.uiService.bus, AppEvent.RESIZE, /** @type {any} */ (this.render));
        this.setupStickyStatusbar();

        const { autofocusFieldIds } = archInfo;
        const rootRef = useRef("compiled_view_root");
        if (this.shouldAutoFocus) {
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
                                    .join(", "),
                            );
                    }
                    if (elementToFocus) {
                        mutate(() => {
                            if (
                                elementToFocus.isConnected &&
                                !rootEl
                                    .querySelector(".o_content")
                                    ?.contains(document.activeElement)
                            ) {
                                elementToFocus.focus();
                            }
                        });
                    }
                },
                () => [this.props.record.isNew, rootRef.el],
            );
        }

        if (this.env.inDialog) {
            const fieldNodeIds = new Set(Object.keys(this.props.archInfo.fieldNodes));
            const elementsByNodeIds = {};
            onMounted(() => {
                if (!rootRef.el) {
                    return;
                }
                for (const el of document.querySelectorAll("[id]")) {
                    const id = el.getAttribute("id");
                    if (id === null) {
                        continue;
                    }
                    if (
                        fieldNodeIds.has(id) &&
                        !(id in elementsByNodeIds) &&
                        !rootRef.el.contains(el)
                    ) {
                        el.removeAttribute("id");
                        elementsByNodeIds[id] = el;
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

    setupStickyStatusbar() {
        const sentinel = useRef("stickySentinel");
        useEffect(
            (el) => {
                if (!el) {
                    return;
                }
                const observer = new IntersectionObserver(
                    ([entry]) => {
                        this.state.isStatusbarStickyPinned =
                            !this.env.inDialog &&
                            !this.env.isSmall &&
                            !entry.isIntersecting;
                    },
                    { root: el.parentElement },
                );
                observer.observe(el);
                return () => observer.disconnect();
            },
            () => [sentinel.el],
        );
    }

    async onWillChangeNotebookPage(
        /** @type {any} */ _notebookId,
        /** @type {any} */ _page,
    ) {
        // flush the edits still pending in the fields before the page leaves them
        await this.props.record.model.askChanges();
        return true;
    }
}
