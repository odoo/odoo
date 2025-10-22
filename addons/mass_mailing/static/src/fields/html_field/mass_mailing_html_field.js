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
import { registry } from "@web/core/registry";
import { Deferred, KeepLast } from "@web/core/utils/concurrency";
import { effect } from "@web/core/utils/reactive";
import { useChildRef, useService } from "@web/core/utils/hooks";

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

        this.keepLastIframe = new KeepLast();
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

        let currentKey;
        effect(
            (state) => {
                if (status(this) === "destroyed") {
                    return;
                }
                if (state.key !== currentKey) {
                    // html value may have been reset from the server:
                    // - await the new iframe
                    this.resetIframe();
                    // - ensure that the activeTheme is up to date.
                    this.updateActiveTheme();
                    currentKey = state.key;
                }
            },
            [this.state]
        );

        // Evaluate if the themeSelector should be displayed
        effect(
            (state) => {
                if (status(this) === "destroyed") {
                    return;
                }
                const activeTheme = state.activeTheme;
                const showThemeSelector = state.showThemeSelector;
                if (!activeTheme && !showThemeSelector && !this.props.readonly) {
                    // Show the ThemeSelector when the theme is unknown and the content can be
                    // changed (invalid value).
                    state.showThemeSelector = true;
                } else if ((activeTheme && showThemeSelector) || this.props.readonly) {
                    state.showThemeSelector = false;
                }
                if (showThemeSelector && toRaw(state.showCodeView)) {
                    // Never show the CodeView with the ThemeSelector.
                    state.showCodeView = false;
                }
            },
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
        this.lastIframeLoaded = this.keepLastIframe.add(this.iframeLoaded);
    }

    onIframeLoad(iframeLoaded) {
        this.iframeLoaded.resolve(iframeLoaded);
    }

    updateActiveTheme() {
        const getThemeName = () => {
            const value = this.value;
            if (!value) {
                return;
            }
            const fragment = parseHTML(document, value);
            const layout = fragment.querySelector(".o_layout");
            if (!layout) {
                return;
            }
            return this.themeService.getThemeName(layout.classList);
        };
        const activeTheme = getThemeName();
        if (toRaw(this.state).activeTheme !== activeTheme) {
            this.state.activeTheme = activeTheme;
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
            mobileBreakpoint: "md",
            defaultImageMimetype: "image/jpeg",
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
            Plugins: [...MAIN_EDITOR_PLUGINS, ...DYNAMIC_PLACEHOLDER_PLUGINS],
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
            await this.lastIframeLoaded;
            this.isDirty = true;
            this.lastValue = undefined;
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
        await this.lastIframeLoaded;
        this.lastValue = normalizeHTML(value, this.clearElementToCompare.bind(this));
        this.isDirty = false;
        const shouldRestoreDisplayNone = this.iframeRef.el.classList.contains("d-none");
        // d-none must be removed for style computation.
        this.iframeRef.el.classList.remove("d-none");
        this.iframeRef.el.style.width = "1320px";
        const processingEl = this.iframeRef.el.contentDocument.createElement("DIV");
        processingEl.append(parseHTML(this.iframeRef.el.contentDocument, value));
        const processingContainer = this.iframeRef.el.contentDocument.querySelector(
            ".o_mass_mailing_processing_container"
        );
        processingContainer.append(processingEl);
        const cssRules = getCSSRules(this.iframeRef.el.contentDocument);
        await toInline(processingEl, cssRules);
        const inlineValue = processingEl.innerHTML;
        processingEl.remove();
        this.iframeRef.el.style.width = "";
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
