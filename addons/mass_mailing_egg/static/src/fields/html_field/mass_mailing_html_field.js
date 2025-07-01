import {
    HtmlMailField,
    htmlMailField,
} from "@mail/views/web/fields/html_mail_field/html_mail_field";
import { registry } from "@web/core/registry";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { MassMailingIframe } from "@mass_mailing_egg/iframe/mass_mailing_iframe";
import { ThemeSelector } from "@mass_mailing_egg/themes/theme_selector/theme_selector";
import { onWillUpdateProps, status, toRaw } from "@odoo/owl";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { useTransition } from "@web/core/transition";
import { effect } from "@web/core/utils/reactive";
import { htmlField, HtmlField } from "@html_editor/fields/html_field";
import { normalizeHTML, parseHTML } from "@html_editor/utils/html";
import { Deferred, Race } from "@web/core/utils/concurrency";
import { useRecordObserver } from "@web/model/relational_model/utils";

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
        Object.assign(this.state, {
            // TODO EGGMAIL: maybe define a condition if there is no content to display
            // theme selectors. Or at least add an interface button to allow changing the theme
            // TODO EGGMAIL: usage of is_body_empty is forbidden, do something else for
            // this heuristic
            showThemeSelector: this.props.record.isNew || this.props.record.data.is_body_empty,
            activeTheme: undefined,
            themeOptions: {
                withBuilder: true,
            },
        });
        useRecordObserver((record) => {
            this.state.showThemeSelector = record.isNew || record.data.is_body_empty;
        });

        this.iframeLoadingRace = new Race();
        this.iframeRef = useChildRef();

        // Use a transition to display the HtmlField only when the themes
        // service finished loading
        this.displayTransition = useTransition({
            name: "mass_mailing_html_field",
            initialVisibility: false,
            immediate: false,
            leaveDuration: 150,
            onLeave: () => {},
        });
        const onThemesLoaded = () => {
            Object.assign(this.displayTransition, {
                class: "o_mass_mailing_themes_loaded",
                shouldMount: true,
            });
            if (!this.state.showThemeSelector) {
                this.updateThemeOptions();
            }
        };
        if (!this.themeService.isLoaded()) {
            const themesPromise = this.themeService.load();
            themesPromise.then(onThemesLoaded);
        } else {
            onThemesLoaded();
        }

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
        });

        // Recompute the themeOptions when the html value changes on the record
        let currentKey;
        effect(
            (state) => {
                if (status(this) === "destroyed") {
                    return;
                }
                if (state.key !== currentKey) {
                    this.updateThemeOptions();
                    this.resetIframe();
                    currentKey = state.key;
                }
            },
            [this.state]
        );
    }

    resetIframe() {
        this.iframeLoaded = new Deferred();
        this.iframeLoadingRace.add(this.iframeLoaded);
    }

    updateThemeOptions() {
        const themeOptions = this.themeService.getThemeOptions(this.value);
        if (toRaw(this.state).activeTheme !== themeOptions.name) {
            this.state.activeTheme = themeOptions.name;
            this.state.themeOptions = themeOptions;
        }
    }

    /**
     * @override
     */
    getConfig() {
        if (this.props.readonly) {
            return this.getReadonlyConfig();
        } else if (this.state.themeOptions?.withBuilder) {
            return this.getBuilderConfig();
        } else {
            return this.getSimpleEditorConfig();
        }
        // TODO EGGMAIL: implement CODEVIEW (iframe d-none, display textarea, apply changes
        // from textarea to iframe, notify editor for a step)
        // TODO EGGMAIL do we want dynamic placeholders?
    }

    /**
     * @override
     */
    getReadonlyConfig() {
        // TODO EGGMAIL ?
        return super.getReadonlyConfig();
    }

    getBuilderConfig() {
        const config = super.getConfig();
        // All plugins for the html builder are defined in mass_mailing_builder
        delete config.Plugins;
        return {
            ...config,
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
            toggleThemeSelector: (show) => this.toggleThemeSelector(show),
        };
    }

    getThemeSelectorConfig() {
        return {
            setThemeOptions: async (themeOptions) => {
                this.state.activeTheme = themeOptions.name;
                this.state.themeOptions = themeOptions;
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
        const inlineValue = await this.getInlineEditorContent().innerHTML;
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
