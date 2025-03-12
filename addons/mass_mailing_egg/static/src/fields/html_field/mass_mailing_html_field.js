import {
    HtmlMailField,
    htmlMailField,
} from "@mail/views/web/fields/html_mail_field/html_mail_field";
import { registry } from "@web/core/registry";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { MassMailingIframe } from "@mass_mailing_egg/iframe/mass_mailing_iframe";
import { ThemeSelector } from "@mass_mailing_egg/themes/theme_selector/theme_selector";

export class MassMailingHtmlField extends HtmlMailField {
    static template = "mass_mailing_egg.HtmlField";
    static components = {
        ...HtmlMailField.components,
        LocalOverlayContainer,
        MassMailingIframe,
        ThemeSelector,
    };

    setup() {
        super.setup();
        this.state.showThemeSelector = this.props.record.isNew;
        Object.assign(this.state, {
            showThemeSelector: this.props.record.isNew,
            themeOptions: undefined,
        });
    }

    /**
     * @override
     */
    getConfig() {
        // TODO EGGMAIL do we want the codeview?
        // TODO EGGMAIL do we want dynamic placeholders?
        return super.getConfig();
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
            // TODO EGGMAIL: allow the builder to show the theme selection again
            // Applying a new Theme from the builder should CREATE AN EDITOR STEP
            // that can be UNDONE.
            showThemeSelector: () => (this.state.showThemeSelector = true),
        };
    }

    getThemeSelectorConfig() {
        return {
            setThemeOptions: (themeOptions) => (this.state.themeOptions = themeOptions),
        };
    }
}

export const massMailingHtmlField = {
    ...htmlMailField,
    component: MassMailingHtmlField,
    // TODO EGGMAIL decide which options we want in extractProps?
};

registry.category("fields").add("mass_mailing_egg_html", massMailingHtmlField);
