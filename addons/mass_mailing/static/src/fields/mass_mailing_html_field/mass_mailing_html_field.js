import { htmlField, HtmlField } from "@html_editor/fields/html_field";
import { JustifyPlugin } from "@html_editor/main/justify_plugin";
import { LinkPopoverPlugin } from "@html_editor/main/link/link_popover_plugin";
import { LinkToolsPlugin } from "@html_editor/main/link/link_tools_plugin";
import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { EventBus, onWillStart, reactive, useRef, useSubEnv } from "@odoo/owl";
import { getBundle, LazyComponent, loadBundle } from "@web/core/assets";
import { ensureJQuery } from "@web/core/ensure_jquery";
import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import weUtils from "@web_editor/js/common/utils";
import { MassMailingTemplateSelector, switchImages } from "./mass_mailing_template_selector";
import { getCSSRules, toInline } from "@mail/views/web/fields/html_mail_field/convert_inline";
import { parseHTML } from "@html_editor/utils/html";

const cssRulesByElement = new WeakMap();
function getCachedCSSRules(el) {
    if (!cssRulesByElement.has(el)) {
        cssRulesByElement.set(el, getCSSRules(el.ownerDocument));
    }
    return cssRulesByElement.get(el);
}

// const legacyEventToNewEvent = {
//     historyStep: "ADD_STEP",
//     historyUndo: "HISTORY_UNDO",
//     historyRedo: "HISTORY_REDO",
// };

export class MassMailingHtmlField extends HtmlField {
    static template = "mass_mailing.MassMailingHtmlField";
    static components = { ...HtmlField.components, LazyComponent, MassMailingTemplateSelector };
    static props = {
        ...HtmlField.props,
        inlineField: { type: String, optional: true },
        filterTemplates: Boolean,
    };

    setup() {
        super.setup();
        this.ui = useService("ui");
        Object.assign(this.state, {
            showMassMailingTemplateSelector: this.value.toString() === "",
            iframeDocument: null,
            toolbarInfos: undefined,
            linkToolState: {
                linkToolProps: undefined,
            },
            isBasicTheme: this.value.toString().search("o_basic_theme") >= 0,
        });
        this.historyState = reactive({
            canUndo: false,
            canRedo: false,
        });

        this.focusEditableOnLoad = false;
        this.snippetsMenuBus = new EventBus();
        useSubEnv({
            switchImages,
            fieldConfig: this.fieldConfig,
        });

        this.editorRef = useRef("editor");

        onWillStart(async () => {
            await Promise.all([
                ensureJQuery(),
                loadBundle("mass_mailing.assets_mass_mailing_html_field"),
            ]);

            this.iframeBundle = getBundle("web_editor.wysiwyg_iframe_editor_assets");
            this.massMailingBundle = getBundle("mass_mailing.iframe_css_assets_edit");

            const { MassMailingSnippetsMenu } = await odoo.loader.modules.get(
                "@mass_mailing/fields/mass_mailing_html_field/mass_mailing_snippet_menu"
            );
            this.MassMailingSnippetsMenu = MassMailingSnippetsMenu;
        });
        this.getColorpickerTemplate = useService("get_color_picker_template");
    }

    onApplyExternalContent(record) {
        super.onApplyExternalContent(...arguments);
        this.resetSnippetsMenu();
        const content = record.data[this.props.name].toString();
        this.state.showMassMailingTemplateSelector = content === "";
        this.state.isBasicTheme = content.search("o_basic_theme") >= 0;
    }

    get displaySnippetsMenu() {
        return (
            this.state.iframeDocument &&
            !this.state.isBasicTheme &&
            !this.ui.isSmall &&
            !this.state.showCodeView
        );
    }

    get snippetMenuProps() {
        const self = this;
        /** @type {import("../../../../../html_editor/static/src/editor").Editor} */
        const state = this.state;
        const options = {
            mutex: new Mutex(),
            snippets: "mass_mailing.email_designer_snippets",
            selectorEditableArea: ".o_editable",
            get document() {
                return state.iframeDocument;
            },
            wysiwyg: {
                get document() {
                    return state.iframeDocument;
                },
                get $editable() {
                    return $(self.editor.editable);
                },
                get $iframe() {
                    return $(self.editorRef.el).find("iframe");
                },
                get lastMediaClicked() {
                    return self.lastMediaClicked;
                },
                getValue: () => this.editor.getContent(),
                getEditable: () => $(self.editor.editable),
                isSaving: () => false,
                getColorpickerTemplate: this.getColorpickerTemplate,
                state: {
                    toolbarProps: {},
                },
                historyState: this.historyState,
                undo: () => {
                    self.editor.dispatch("HISTORY_UNDO");
                },
                redo: () => {
                    self.editor.dispatch("HISTORY_REDO");
                },
                openMediaDialog() {
                    self.editor.dispatch("REPLACE_IMAGE");
                },
                odooEditor: {
                    get document() {
                        return state.iframeDocument;
                    },

                    addEventListener: (legacyEvent) => {
                        // const event = legacyEventToNewEvent[legacyEvent];
                        // if (!event) {
                        //     throw new Error(`Missing event to map ${legacyEvent}`);
                        // }
                    },
                    removeEventListener() {},

                    /**
                     * Find all descendants of `element` with a `data-call` attribute and bind
                     * them on click to the execution of the command matching that
                     * attribute.
                     */
                    bindExecCommand(element) {
                        const editor = self.editor;
                        const commands = {
                            removeFormat: "FORMAT_REMOVE_FORMAT",
                            addColumn: (el) => {
                                editor.dispatch("ADD_COLUMN", {
                                    position: el.dataset.arg1,
                                    reference: closestElement(
                                        editor.shared.getEditableSelection().anchorNode,
                                        "td"
                                    ),
                                });
                            },
                            addRow: (el) => {
                                editor.dispatch("ADD_ROW", {
                                    position: el.dataset.arg1,
                                    reference: closestElement(
                                        editor.shared.getEditableSelection().anchorNode,
                                        "tr"
                                    ),
                                });
                            },
                            removeColumn: (el) => {
                                editor.dispatch("REMOVE_COLUMN", {
                                    cell: closestElement(
                                        editor.shared.getEditableSelection().anchorNode,
                                        "td"
                                    ),
                                });
                            },
                            removeRow: (el) => {
                                editor.dispatch("REMOVE_ROW", {
                                    row: closestElement(
                                        editor.shared.getEditableSelection().anchorNode,
                                        "tr"
                                    ),
                                });
                            },
                            resetSize: (el) => {
                                editor.dispatch("RESET_SIZE", {
                                    table: closestElement(
                                        editor.shared.getEditableSelection().anchorNode,
                                        "table"
                                    ),
                                });
                            },
                        };
                        for (const buttonEl of element.querySelectorAll("[data-call]")) {
                            buttonEl.addEventListener("click", (ev) => {
                                const command = commands[buttonEl.dataset.call];
                                if (!command) {
                                    return;
                                }
                                ev.preventDefault();
                                if (typeof command === "function") {
                                    command(buttonEl);
                                } else {
                                    editor.dispatch(command);
                                }
                            });
                        }
                    },
                    computeFontSizeSelectorValues() {},

                    historyStep() {
                        self.editor.dispatch("ADD_STEP");
                    },

                    historyPauseSteps() {},
                    historyUnpauseSteps() {},

                    historyResetLatestComputedSelection() {},
                    historyRevertCurrentStep() {},

                    automaticStepSkipStack() {},
                    automaticStepActive() {},
                    automaticStepUnactive() {},

                    observerActive() {},
                    observerUnactive() {},
                    sanitize() {},

                    unbreakableStepUnactive() {},
                },
            },
        };
        return {
            bus: this.snippetsMenuBus,
            folded: false,
            options,
            setCSSVariables: (element) => {
                const stylesToCopy = weUtils.EDITOR_COLOR_CSS_VARIABLES;

                for (const style of stylesToCopy) {
                    let value = weUtils.getCSSVariableValue(style);
                    if (value.startsWith("'") && value.endsWith("'")) {
                        // Gradient values are recovered within a string.
                        value = value.substring(1, value.length - 1);
                    }
                    element.style.setProperty(`--we-cp-${style}`, value);
                }

                element.classList.toggle(
                    "o_we_has_btn_outline_primary",
                    weUtils.getCSSVariableValue("btn-primary-outline") === "true"
                );
                element.classList.toggle(
                    "o_we_has_btn_outline_secondary",
                    weUtils.getCSSVariableValue("btn-secondary-outline") === "true"
                );
            },
            trigger_up: (ev) => this._trigger_up(ev),
            toolbarInfos: state.toolbarInfos,
            toggleCodeView: this.toggleCodeView.bind(this),
            linkToolProps: state.linkToolState.linkToolProps,
            selectedTheme: state.selectedTheme,
        };
    }
    async onSelectMassMailingTemplate(templateInfos, templateHTML) {
        await this.updateValue(templateHTML);
        await this.updateInlineField(parseHTML(document, templateHTML).children[0]);
        this.state.showMassMailingTemplateSelector = false;
        this.state.isBasicTheme = templateInfos.name === "basic";
        if (templateInfos.name === "basic") {
            this.focusEditableOnLoad = true;
        }

        this.state.selectedTheme = templateInfos;
    }

    // -----------------------------------------------------------------------------
    // Legacy compatibility layer
    // Remove me when all legacy widgets using wysiwyg are converted to OWL.
    // -----------------------------------------------------------------------------
    _trigger_up(ev) {
        const evType = ev.name;
        const payload = ev.data;
        if (evType === "call_service") {
            this._callService(payload);
        }
    }
    _callService(payload) {
        const service = this.env.services[payload.service];
        const result = service[payload.method].apply(service, payload.args || []);
        payload.callback(result);
    }

    get wysiwygProps() {
        const props = super.wysiwygProps;
        return {
            ...props,
            class: "h-100",
            contentClass: "o_in_iframe",
            iframe: true,
            onIframeLoaded: async (doc, editor) => {
                await this.populateIframeDocument(doc);
                this.state.iframeDocument = doc;
                const editable = doc.createElement("div");
                doc.body.append(editable);
                editor.attachTo(editable);

                this.state.linkToolState = this.editor.shared.getLinktoolState();

                this.bindLastMediaClicked(doc);

                if (this.focusEditableOnLoad) {
                    this.editor.editable.focus();
                    this.shouldFocusOnLoad = false;
                }

                this.state.toolbarInfos = this.editor.shared.getToolbarInfo();
            },
            // copyCss: true,
        };
    }

    getConfig() {
        const config = super.getConfig(...arguments);
        config.Plugins = config.Plugins.filter((x) => x !== LinkPopoverPlugin);
        config.Plugins.push(JustifyPlugin);
        config.Plugins.push(LinkToolsPlugin);
        config.Plugins.push(DragBlockPlugin);
        config.getColorpickerTemplate = this.getColorpickerTemplate;
        config.disableFloatingToolbar = true;
        config.disabledToolbarButtonIds = new Set(["remove_format", "codeview"]);
        config.resources = Object.assign({}, config.resources, {
            toolbarItems: [
                ...(config.resources?.toolbarItems || []),
                {
                    id: "insert_media",
                    category: "link",
                    name: "Insert Media",
                    icon: "fa-file-image-o",
                    action(dispatch) {
                        dispatch("INSERT_MEDIA");
                    },
                },
            ],
        });
        return config;
    }

    resetSnippetsMenu() {
        this.state.iframeDocument = null;
        this.historyState.canUndo = false;
        this.historyState.canRedo = false;
    }

    async getEditorContent() {
        if (this.displaySnippetsMenu) {
            const cleanedProms = [];
            this.snippetsMenuBus.trigger("CLEAN_FOR_SAVE", { proms: cleanedProms });
            await Promise.all(cleanedProms);
        }
        const el = await super.getEditorContent();
        return el;
    }

    async updateCodeview(content) {
        await super.updateCodeview(...arguments);
        return this.updateInlineField(parseHTML(document, content).children[0]);
    }

    async updateEditorContent(el) {
        await super.updateEditorContent(...arguments);
        await this.updateInlineField(el);
    }

    async updateInlineField(el) {
        el.classList.remove("odoo-editor-editable");
        let temporaryIframe;
        if (!this.state.iframeDocument) {
            temporaryIframe = await this.makeIframe();
        }
        const iframeDocument = this.state.iframeDocument || temporaryIframe.contentDocument;
        iframeDocument.body.append(el);
        if (el.querySelector(".o_basic_theme")) {
            for (const element of el.querySelectorAll("*")) {
                element.style["font-family"] = "";
            }
        }
        await toInline(el, getCachedCSSRules(el));
        el.remove();
        const fieldName = this.props.inlineField;
        await this.props.record.update({ [fieldName]: el.innerHTML });
        if (temporaryIframe) {
            temporaryIframe.remove();
        }
    }

    async makeIframe() {
        const iframe = document.createElement("iframe");
        iframe.style.height = "0px";
        iframe.style.visibility = "hidden";
        // Make sure no scripts get executed.
        iframe.setAttribute("sandbox", "allow-same-origin");
        const iframePromise = new Promise((resolve) => {
            iframe.addEventListener("load", resolve, { once: true });
        });
        document.body.append(iframe);
        await iframePromise;
        await this.populateIframeDocument(iframe.contentDocument, { loadJS: false });
        return iframe;
    }

    async populateIframeDocument(doc, { loadJS = true } = {}) {
        doc.body.classList.add("editor_enable");
        doc.body.classList.add("o_mass_mailing_iframe");
        doc.body.classList.add("o_in_iframe");
        const iframeBundle = await this.iframeBundle;
        const massMailingBundle = await this.massMailingBundle;
        function addStyle(href) {
            const link = doc.createElement("link");
            link.rel = "stylesheet";
            link.href = href;
            const promise = new Promise((resolve, reject) => {
                link.onload = resolve;
                link.onerror = reject;
            });
            doc.head.appendChild(link);
            return promise;
        }
        function addScript(src) {
            const script = doc.createElement("script");
            script.type = "text/javascript";
            script.src = src;
            const promise = new Promise((resolve, reject) => {
                script.onload = resolve;
                script.onerror = reject;
            });
            doc.head.appendChild(script);
            return promise;
        }
        await Promise.all([
            addStyle(iframeBundle.cssLibs[0]),
            addStyle(massMailingBundle.cssLibs[0]),
            loadJS && addScript(iframeBundle.jsLibs[0]),
        ]);
    }

    onChange() {
        super.onChange(...arguments);
        Object.assign(this.historyState, {
            canUndo: this.editor.isDestroyed ? false : this.editor.shared.canUndo(),
            canRedo: this.editor.isDestroyed ? false : this.editor.shared.canRedo(),
        });
    }

    toggleCodeView() {
        super.toggleCodeView();
        this.resetSnippetsMenu();
    }

    /**
     * Bind the last media clicked in the iframe to the lastMediaClicked
     * property.
     *
     * @param {Document} doc
     */
    bindLastMediaClicked(doc) {
        const basicMediaSelector = "img, .fa, .o_image, .media_iframe_video";
        // (see isImageSupportedForStyle).
        const mediaSelector = basicMediaSelector
            .split(",")
            .map((s) => `${s}:not([data-oe-xpath])`)
            .join(",");
        doc.defaultView.addEventListener(
            "mousedown",
            (e) => {
                const isInMedia =
                    e.target &&
                    e.target.matches(mediaSelector) &&
                    !e.target.parentElement.classList.contains("o_stars") &&
                    (e.target.isContentEditable || e.target.parentElement?.isContentEditable);
                this.lastMediaClicked = isInMedia && e.target;
            },
            true
        );
    }
}

class DragBlockPlugin extends Plugin {
    setup() {
        const subEditable = this.editable.querySelector(".o_editable");
        if (subEditable) {
            if (subEditable.getAttribute("data-editor-message") === null) {
                subEditable.setAttribute("data-editor-message", "DRAG BUILDING BLOCKS HERE");
            }
            if (!subEditable.innerHTML.trim()) {
                // The contenteditable true should be set when dropping a snippet inside the editable.
                subEditable.setAttribute("contenteditable", false);
            }
        }
    }
}

export const massMailingHtmlField = {
    // ...htmlField,
    component: MassMailingHtmlField,
    additionalClasses: ["o_field_html"],

    // displayName: _t("Email"),
    // supportedOptions: [...htmlField.supportedOptions, {
    //     label: _t("Filter templates"),
    //     name: "filterTemplates",
    //     type: "boolean"
    // }, {
    //     label: _t("Inline field"),
    //     name: "inline-field",
    //     type: "field"
    // }],
    extractProps({ attrs, options }) {
        const props = htmlField.extractProps(...arguments);
        props.filterTemplates = Boolean(options.filterTemplates);
        props.inlineField = options["inline-field"];
        return props;
    },
    // fieldDependencies: [{ name: 'body_html', type: 'html', readonly: 'false' }],
};

registry.category("fields").add("mass_mailing_html", massMailingHtmlField);
