import {
    HtmlMailField,
    htmlMailField,
} from "@mail/views/web/fields/html_mail_field/html_mail_field";
import { registry } from "@web/core/registry";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { MassMailingIframe } from "@mass_mailing_egg/iframe/mass_mailing_iframe";
import { ThemeSelector } from "@mass_mailing_egg/themes/theme_selector/theme_selector";
import { onWillUpdateProps, status, toRaw } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useTransition } from "@web/core/transition";
import { effect } from "@web/core/utils/reactive";
import { htmlField, HtmlField } from "@html_editor/fields/html_field";

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
    };

    setup() {
        super.setup();
        this.themeService = useService("mass_mailing_egg.themes");
        Object.assign(this.state, {
            // TODO EGGMAIL: maybe define a condition if there is no content to display
            // theme selectors. Or at least add an interface button to allow changing the theme
            showThemeSelector: this.props.record.isNew,
            activeTheme: undefined,
            themeOptions: {
                withBuilder: true,
            },
        });

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
        onWillUpdateProps((nextProps) => {
            if (
                this.props.readonly !== nextProps.readonly &&
                (this.props.readonly || nextProps.readonly)
            ) {
                this.state.key++;
            }
        });

        // Recompute the themeOptions when the html value changes on the record
        let currentKey = this.state.key;
        effect(
            (state) => {
                if (status(this) === "destroyed") {
                    return;
                }
                if (state.key !== currentKey) {
                    this.updateThemeOptions();
                    currentKey = state.key;
                }
            },
            [this.state]
        );
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
        return {
            content: this.value,
            // TODO EGGMAIL?: allow the builder to show the theme selection again
            // Applying a new Theme from the builder should CREATE AN EDITOR STEP
            // that can be UNDONE.
            showThemeSelector: () => (this.state.showThemeSelector = true),
        };
    }

    getSimpleEditorConfig() {
        // TODO EGGMAIL: special config for no-builder mode
        return super.getConfig();
    }

    getThemeSelectorConfig() {
        return {
            setThemeOptions: async (themeOptions) => {
                this.state.activeTheme = themeOptions.name;
                this.state.themeOptions = themeOptions;
                this.state.showThemeSelector = false;
                await this.updateValue(themeOptions.html);
            },
            filterTemplates: this.props.filterTemplates,
            mailingModelId: this.props.record.data.mailing_model_id.id,
            mailingModelName: this.props.record.data.mailing_model_id.display_name || "",
        };
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
            migrateHTML: false,
            embeddedComponents: false,
        });
        return props;
    },
    fieldDependencies: [{ name: "body_html", type: "html", readonly: "false" }],
};

registry.category("fields").add("mass_mailing_egg_html", massMailingHtmlField);
