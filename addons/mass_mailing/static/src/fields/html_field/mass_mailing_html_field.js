import { DYNAMIC_PLACEHOLDER_PLUGINS } from "@html_editor/backend/plugin_sets";
import { htmlField, HtmlField } from "@html_editor/fields/html_field";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { MAIN_PLUGINS as MAIN_EDITOR_PLUGINS } from "@html_editor/plugin_sets";
import { normalizeHTML, parseHTML } from "@html_editor/utils/html";
import { MassMailingIframe } from "@mass_mailing/iframe/mass_mailing_iframe";
import { ThemeSelector } from "@mass_mailing/themes/theme_selector/theme_selector";
import { getCSSRules, toInline } from "@mail/views/web/fields/html_mail_field/convert_inline";
import { onWillUpdateProps, status, toRaw, useEffect, useRef } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { effect } from "@web/core/utils/reactive";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { batched } from "@web/core/utils/timing";
import { PowerButtonsPlugin } from "@html_editor/main/power_buttons_plugin";

export class MassMailingHtmlField extends HtmlField {
    static template = "mass_mailing.HtmlField";
    static components = {
        ...HtmlField.components,
        LocalOverlayContainer,
        MassMailingIframe,
        ThemeSelector,
    };
    static props = {
        ...HtmlField.props,
        inlineField: { type: String },
        filterTemplates: { type: Boolean, optional: true },
    };

    setup() {
        // Keep track of the next props before other `onWillUpdateProps`
        // callbacks in super can be executed, to be able to compute the next
        // activeTheme and next themeSelector display status just before the
        // Component is patched.
        let props = this.props;
        onWillUpdateProps((nextProps) => {
            if (nextProps !== this.props) {
                props = nextProps;
            }
        });
        super.setup();
        this.themeService = useService("mass_mailing.themes");
        this.ui = useService("ui");
        Object.assign(this.state, {
            showThemeSelector: this.props.record.isNew,
            activeTheme: undefined,
        });

        if (this.state.showThemeSelector) {
            // Preemptively load assets for the html Builder because
            // there is a high chance that they will be needed from the
            // Theme Selector, no need to wait for the user selection.
            loadBundle("mass_mailing.assets_builder");
        }

        this.resetIframe();
        this.iframeRef = useChildRef();
        this.codeViewButtonRef = useRef("codeViewButtonRef");

        onWillUpdateProps((nextProps) => {
            if (
                this.props.readonly !== nextProps.readonly &&
                (this.props.readonly || nextProps.readonly)
            ) {
                // Force a full reload for MassMailingIframe on readonly change
                this.state.key++;
            }
            if (nextProps.readonly) {
                toRaw(this.state).showThemeSelector = false;
            }
            if (nextProps.record.isNew) {
                Object.assign(toRaw(this.state), {
                    activeTheme: undefined,
                    showCodeView: false,
                    showThemeSelector: true,
                });
            }
        });

        let currentKey = this.state.key;
        effect(
            batched((state) => {
                if (status(this) === "destroyed") {
                    return;
                }
                if (state.key !== currentKey) {
                    // html value may have been reset from the server:
                    // - await the new iframe
                    this.resetIframe();
                    // - ensure that the activeTheme is up to date with the next
                    //   record.
                    this.updateActiveTheme(props.record);
                    // - ensure that the themeSelector is displayed if necessary
                    //   for the next props.
                    this.updateThemeSelector(props);
                    currentKey = state.key;
                }
            }),
            [this.state]
        );

        useEffect(
            () => {
                if (!this.codeViewRef.el) {
                    return;
                }
                // Set the initial textArea height.
                this.codeViewRef.el.style.height = this.codeViewRef.el.scrollHeight + "px";
            },
            () => [this.codeViewRef.el]
        );
    }

    get withBuilder() {
        return !this.props.readonly && this.state.activeTheme !== "basic";
    }

    resetIframe() {
        this.iframeLoaded = new Deferred();
    }

    async ensureIframeLoaded() {
        const iframeLoaded = this.iframeLoaded;
        const iframeInfo = await iframeLoaded;
        return iframeLoaded === this.iframeLoaded ? iframeInfo : undefined;
    }

    onIframeLoad(iframeLoaded) {
        this.iframeLoaded.resolve(iframeLoaded);
    }

    updateActiveTheme(record = this.props.record) {
        // This function is called in an `effect` with a dependency on
        // `state.key` which already guarantees that the Component will be
        // re-rendered. All further reads on the state should not add
        // dependencies to that effect, so it is used raw.
        const state = toRaw(this.state);
        const getThemeName = () => {
            const value = record.data[this.props.name];
            if (!value || !value.toString()) {
                return;
            }
            const fragment = parseHTML(document, value);
            const layout = fragment.querySelector(".o_layout");
            if (!layout) {
                return "unknown";
            }
            return this.themeService.getThemeName(layout.classList) || "unknown";
        };
        const activeTheme = getThemeName();
        if (state.activeTheme !== activeTheme) {
            state.activeTheme = activeTheme;
        }
    }

    updateThemeSelector(props = this.props) {
        // This function is called in an `effect` with a dependency on
        // `state.key` which already guarantees that the Component will be
        // re-rendered. All further reads on the state should not add
        // dependencies to that effect, so it is used raw.
        const state = toRaw(this.state);
        if (!state.activeTheme && !state.showThemeSelector && !props.readonly) {
            // Show the ThemeSelector when the theme is undefined and the content can be
            // changed.
            state.showThemeSelector = true;
        } else if ((state.activeTheme && state.showThemeSelector) || props.readonly) {
            state.showThemeSelector = false;
        }
        if (state.showThemeSelector && state.showCodeView) {
            // Never show the CodeView with the ThemeSelector.
            state.showCodeView = false;
        }
    }

    getMassMailingIframeProps() {
        const props = {
            config: this.getConfig(),
            iframeRef: this.iframeRef,
            onBlur: this.onBlur.bind(this),
            onEditorLoad: this.onEditorLoad.bind(this),
            onIframeLoad: this.onIframeLoad.bind(this),
            readonly: this.props.readonly,
            showThemeSelector: this.state.showThemeSelector,
            showCodeView: this.state.showCodeView,
            withBuilder: this.withBuilder,
        };
        if (this.env.debug) {
            Object.assign(props, {
                toggleCodeView: () => this.toggleCodeView(),
            });
        }
        return props;
    }

    /**
     * Content reinsertion as done in the super method is not properly supported
     * by the editor (corrupted state). This override forces the creation of
     * a new editor instead, and all plugins will be instantiated from scratch.
     * @override
     */
    async toggleCodeView() {
        await this.commitChanges();
        this.state.showCodeView = !this.state.showCodeView;
        this.state.key++;
    }

    /**
     * @override
     */
    getConfig() {
        if (this.props.readonly) {
            return this.getReadonlyConfig();
        } else if (this.withBuilder) {
            return this.getBuilderConfig();
        } else {
            return this.getSimpleEditorConfig();
        }
    }

    /**
     * @override
     */
    getReadonlyConfig() {
        const config = super.getReadonlyConfig();
        config.value =
            config.value && config.value.toString()
                ? config.value
                : this.props.record.data[this.props.inlineField];
        return config;
    }

    getBuilderConfig() {
        const config = super.getConfig();
        // All plugins for the html Builder are defined in MassMailingBuilder
        delete config.Plugins;
        return {
            ...config,
            allowChecklist: false,
            record: this.props.record,
            mobileBreakpoint: "md",
            defaultImageMimetype: "image/png",
            onEditorReady: () => this.commitChanges(),
        };
    }

    getSimpleEditorConfig() {
        const config = super.getConfig();
        const codeViewCommand = [config.resources?.user_commands]
            .filter(Boolean)
            .flat()
            .find((cmd) => cmd.id === "codeview");
        if (codeViewCommand) {
            codeViewCommand.isAvailable = () => this.env.debug;
        }
        return {
            ...config,
            onEditorReady: () => this.commitChanges(),
            Plugins: [
                ...MAIN_EDITOR_PLUGINS,
                ...DYNAMIC_PLACEHOLDER_PLUGINS,
                ...registry.category("basic-editor-plugins").getAll(),
                PowerButtonsPlugin,
            ].filter((P) => !["banner", "prompt"].includes(P.id)),
        };
    }

    getThemeSelectorConfig() {
        return {
            setThemeHTML: (html) =>
                this.mutex.exec(() =>
                    // The inlineField can not be updated to its final value at
                    // this point since the editor is needed to process the
                    // theme template. (i.e. applying the default style).
                    // It will be updated onEditorReady since it has become empty.
                    this.props.record
                        .update({
                            [this.props.name]: html,
                            [this.props.inlineField]: "",
                        })
                        .catch(() => {})
                ),
            filterTemplates: this.props.filterTemplates,
            mailingModelId: this.props.record.data.mailing_model_id.id,
            mailingModelName: this.props.record.data.mailing_model_id.display_name || "",
        };
    }

    onTextareaInput(ev) {
        this.onChange();
        ev.target.style.height = ev.target.scrollHeight + "px";
    }

    /**
     * Ensure that the inlineField has its first value set (in case a template
     * was just applied or if the field value was set manually without using
     * this widget.
     * @override
     */
    async _commitChanges({ urgent }) {
        if (
            this.editor &&
            !this.editor.isDestroyed &&
            this.props.record.data[this.props.inlineField].toString() === ""
        ) {
            if ((await this.ensureIframeLoaded()) && this.editor && !this.editor.isDestroyed) {
                this.isDirty = true;
                this.lastValue = undefined;
            } else {
                return;
            }
        }
        if (!this.state.showCodeView && this.editor?.isDestroyed) {
            return;
        }
        return super._commitChanges({ urgent });
    }

    /**
     * Complete rewrite of `updateValue` to ensure that both the field and the
     * inlineField are saved at the same time. Depends on the iframe to compute
     * the style of the inlineField.
     * @override
     */
    async updateValue(value) {
        const iframeInfo = await this.ensureIframeLoaded();
        if (!iframeInfo) {
            return;
        }
        const { bundleControls } = iframeInfo;
        this.lastValue = normalizeHTML(value, this.clearElementToCompare.bind(this));
        this.isDirty = false;
        const shouldRestoreDisplayNone = this.iframeRef.el.classList.contains("d-none");
        // d-none must be removed for style computation.
        this.iframeRef.el.classList.remove("d-none");
        // The browser resets the size of the `iframe` inside `toInline`
        // if we just set `width`. So as a workaround we set both `min-width`
        // and `max-width` to force the size of the `iframe` for a proper
        // inline conversion.
        this.iframeRef.el.style.setProperty("min-width", "1320px", "important");
        this.iframeRef.el.style.setProperty("max-width", "1320px", "important");
        const processingEl = this.iframeRef.el.contentDocument.createElement("DIV");
        processingEl.append(parseHTML(this.iframeRef.el.contentDocument, value));
        const processingContainer = this.iframeRef.el.contentDocument.querySelector(
            ".o_mass_mailing_processing_container"
        );
        bundleControls["mass_mailing.assets_inside_builder_iframe"]?.toggle(false);
        processingContainer.append(processingEl);
        this.preprocessFilterDomains(processingEl);
        const cssRules = getCSSRules(this.iframeRef.el.contentDocument);
        await toInline(processingEl, cssRules);
        const inlineValue = processingEl.innerHTML;
        processingEl.remove();
        bundleControls["mass_mailing.assets_inside_builder_iframe"]?.toggle(true);
        this.iframeRef.el.style.minWidth = "";
        this.iframeRef.el.style.maxWidth = "";
        if (shouldRestoreDisplayNone) {
            this.iframeRef.el.classList.add("d-none");
        }
        await this.props.record
            .update({
                [this.props.name]: value,
                [this.props.inlineField]: inlineValue,
            })
            .catch(() => (this.isDirty = true));
        this.props.record.model.bus.trigger("FIELD_IS_DIRTY", this.isDirty);
    }
    /**
     * Processes the data-filter-domain to be converted to a t-if that will be interpreted on send
     * by QWeb.
     * TODO EGGMAIL: move in a convert_inline plugin when they are implemented.
     * @param {HTMLElement} htmlEl
     */
    preprocessFilterDomains(htmlEl) {
        htmlEl.querySelectorAll("[data-filter-domain]").forEach((el) => {
            let domain;
            try {
                domain = new Domain(JSON.parse(el.dataset.filterDomain));
            } catch {
                el.setAttribute("t-if", "false");
                return;
            }
            el.setAttribute("t-if", `object.filtered_domain(${domain.toString()})`);
        });
    }
}

export const massMailingHtmlField = {
    ...htmlField,
    component: MassMailingHtmlField,
    extractProps({ attrs, options }) {
        const props = htmlField.extractProps(...arguments);
        props.editorConfig.allowChecklist = false;
        props.editorConfig.allowVideo = false;
        props.editorConfig.baseContainers = ["P"];
        Object.assign(props, {
            filterTemplates: options.filterTemplates,
            inlineField: options["inline_field"],
            migrateHTML: false,
            embeddedComponents: false,
            isCollaborative: false,
            sandboxedPreview: false,
            codeview: true,
        });
        return props;
    },
    fieldDependencies: [{ name: "body_html", type: "html", readonly: "false" }],
};

registry.category("fields").add("mass_mailing_html", massMailingHtmlField);
