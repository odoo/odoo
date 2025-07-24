import {
    HtmlMailField,
    htmlMailField,
} from "@mail/views/web/fields/html_mail_field/html_mail_field";
import { registry } from "@web/core/registry";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { MassMailingIframe } from "@mass_mailing_egg/iframe/mass_mailing_iframe";
import { ThemeSelector } from "@mass_mailing_egg/themes/theme_selector/theme_selector";
import { onWillUpdateProps, status, toRaw, useEffect, useRef } from "@odoo/owl";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { useTransition } from "@web/core/transition";
import { effect } from "@web/core/utils/reactive";
import { htmlField, HtmlField } from "@html_editor/fields/html_field";
import { normalizeHTML, parseHTML } from "@html_editor/utils/html";
import { Deferred, Race } from "@web/core/utils/concurrency";
import { MAIN_PLUGINS as MAIN_EDITOR_PLUGINS } from "@html_editor/plugin_sets";
import { DynamicPlaceholderPlugin } from "@html_editor/others/dynamic_placeholder_plugin";

export class MassMailingHtmlField extends HtmlMailField {
    static template = "mass_mailing_egg.HtmlField";
    static components = {
        ...HtmlMailField.components,
        LocalOverlayContainer,
        MassMailingIframe,
        ThemeSelector,
    };
    static props = {
        ...HtmlField.props,
        filterTemplates: { type: Boolean, optional: true },
        inlineField: { type: String, optional: true },
    };

    setup() {
        super.setup();
        this.alwaysComputeInlineEditorContent = false;
        this.themeService = useService("mass_mailing_egg.themes");
        this.ui = useService("ui");
        Object.assign(this.state, {
            showThemeSelector: this.props.record.isNew,
            activeTheme: undefined,
            themeOptions: {
                withBuilder: true,
            },
        });

        this.iframeLoadingRace = new Race();
        this.iframeRef = useChildRef();
        this.codeViewButtonRef = useRef("codeViewButtonRef");

        // Use a transition to display the HtmlField only when the themes
        // service finished loading
        this.displayTransition = useTransition({
            name: "mass_mailing_html_field",
            initialVisibility: false,
            immediate: false,
            leaveDuration: 150,
            onLeave: () => {},
        });

        // Force a full reload for MassMailingIframe on readonly change
        // TODO EGGMAIL probably need a full reload when switching from normal
        // editor to builder? maybe it never happens
        onWillUpdateProps((nextProps) => {
            if (
                this.props.readonly !== nextProps.readonly &&
                (this.props.readonly || nextProps.readonly)
            ) {
                this.state.key++;
            }
            if (nextProps.record.isNew) {
                this.state.activeTheme = undefined;
            }
        });

        // Recompute the themeOptions when the html value changes on the record
        let currentKey;
        effect(
            (state) => {
                if (status(this) === "destroyed") {
                    return;
                }
                if (state.key !== currentKey) {
                    this.updateActiveTheme();
                    this.resetIframe();
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
                if (!activeTheme) {
                    // Always show the theme selector when the theme is unknown
                    state.showThemeSelector = true;
                }
                if (showThemeSelector && toRaw(state.showCodeView)) {
                    // Ensure that the code view is always disabled when the theme selector
                    // is displayed
                    state.showCodeView = false;
                }
            },
            [this.state]
        );
        // Sets the iframe height
        useEffect(
            () => {
                if (!this.codeViewRef.el) {
                    return;
                }
                this.codeViewRef.el.style.height = this.codeViewRef.el.scrollHeight + "px";
            },
            () => [this.codeViewRef.el]
        );
    }

    get isIframeReadonly() {
        return this.props.readonly;
    }

    get withBuilder() {
        return this.state.activeTheme !== "basic";
    }

    resetIframe() {
        this.iframeLoaded = new Deferred();
        this.iframeLoadingRace.add(this.iframeLoaded);
    }

    updateActiveTheme() {
        const activeTheme = this.themeService.getThemeName(this.value);
        if (toRaw(this.state).activeTheme !== activeTheme) {
            this.state.activeTheme = activeTheme;
        }
    }

    getMassMailingIframeProps() {
        const props = {};
        if (this.env.debug) {
            Object.assign(props, {
                toggleCodeView: () => this.toggleCodeView(),
            });
        }
        return props;
    }

    /**
     * @override
     */
    getConfig() {
        if (this.isIframeReadonly) {
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
        return super.getReadonlyConfig();
    }

    getBuilderConfig() {
        const config = super.getConfig();
        // All plugins for the html builder are defined in mass_mailing_builder
        delete config.Plugins;
        return {
            ...config,
            withBuilder: true,
            // TODO EGGMAIL?: allow the builder to show the theme selection again
            // Applying a new Theme from the builder should CREATE AN EDITOR STEP
            // that can be UNDONE.
            toggleThemeSelector: (show) => this.toggleThemeSelector(show),
        };
    }

    getSimpleEditorConfig() {
        // TODO EGGMAIL: special config for no-builder mode
        return {
            ...super.getConfig(),
            Plugins: [...MAIN_EDITOR_PLUGINS, DynamicPlaceholderPlugin],
            toggleThemeSelector: (show) => this.toggleThemeSelector(show),
        };
    }

    getThemeSelectorConfig() {
        return {
            setThemeOptions: async (themeOptions) => {
                this.state.activeTheme = themeOptions.name;
                await this.updateValue(themeOptions.html);
                this.state.showThemeSelector = false;
            },
            filterTemplates: this.props.filterTemplates,
            mailingModelId: this.props.record.data.mailing_model_id.id,
            mailingModelName: this.props.record.data.mailing_model_id.display_name || "",
        };
    }

    onIframeLoad(iframeLoaded) {
        this.iframeLoaded.resolve(iframeLoaded);
    }

    toggleThemeSelector(show = true) {
        this.state.showThemeSelector = show;
    }

    /**
     * Process the content at a specifically designed location to avoid
     * interference with the UI.
     * @override
     */
    insertForInlineProcessing(el) {
        const processingContainer = this.iframeRef.el.contentDocument.querySelector(
            ".o_mass_mailing_processing_container"
        );
        processingContainer.append(el);
    }

    onTextareaInput(ev) {
        ev.target.style.height = ev.target.scrollHeight + "px";
    }

    /**
     * Complete rewrite of `updateValue` to ensure that both the field and the
     * inlineField are saved at the same time. Depends on the iframe to compute
     * the style of the inlineField.
     * TODO EGGMAIL: this is too slow for urgent save. We should display the
     * save confirmation popup like in website on beforeUnload, unlike other
     * html_fields in form views.
     * @override
     */
    async updateValue(value) {
        await this.iframeLoadingRace.getCurrentProm();
        this.lastValue = normalizeHTML(value, this.clearElementToCompare.bind(this));
        this.isDirty = false;
        const shouldRestoreDisplayNone = this.iframeRef.el.classList.contains("d-none");
        this.iframeRef.el.classList.remove("d-none");
        const processingEl = this.iframeRef.el.contentDocument.createElement("DIV");
        processingEl.append(parseHTML(this.iframeRef.el.contentDocument, value));
        this.insertForInlineProcessing(processingEl);
        const inlineValue = (
            await HtmlMailField.getInlineHTML(processingEl, this.iframeRef.el.contentDocument)
        ).innerHTML;
        processingEl.remove();
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
    ...htmlMailField,
    component: MassMailingHtmlField,
    // TODO EGGMAIL decide which options we want in extractProps?
    extractProps({ attrs, options }) {
        const props = htmlField.extractProps(...arguments);
        Object.assign(props, {
            filterTemplates: options.filterTemplates,
            inlineField: options["inline_field"],
            migrateHTML: false,
            embeddedComponents: false,
        });
        return props;
    },
    fieldDependencies: [{ name: "body_html", type: "html", readonly: "false" }],
};

registry.category("fields").add("mass_mailing_egg_html", massMailingHtmlField);
