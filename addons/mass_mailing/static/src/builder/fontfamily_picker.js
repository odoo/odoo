import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { MassMailingBuilderSelectLabel } from "./components/mass_mailing_builder_select_label";
import { _t } from "@web/core/l10n/translation";
import { GOOGLE_FONTS } from "../iframe/mass_mailing_iframe_utils";

const EMAIL_SAFE_FONTS = {
    Arial: "Arial,Helvetica Neue,Helvetica,sans-serif",
    "Courier New": "Courier New,Courier,Lucida Sans Typewriter,Lucida Typewriter,monospace",
    Georgia: "Georgia,Times,Times New Roman,serif",
    "Helvetica Neue": "Helvetica Neue,Helvetica,Arial,sans-serif",
    "Lucida Grande": "Lucida Grande,Lucida Sans Unicode,Lucida Sans,Geneva,Verdana,sans-serif",
    Tahoma: "Tahoma,Verdana,Segoe,sans-serif",
    "Times New Roman": "TimesNewRoman,Times New Roman,Times,Baskerville,Georgia,serif",
    "Trebuchet MS": "Trebuchet MS,Lucida Grande,Lucida Sans Unicode,Lucida Sans,Tahoma,sans-serif",
    Verdana: "Verdana,Geneva,sans-serif",
};

const WEB_SUPPORTED_FONTS = {
    "Lucida Sans": "Lucida Sans,Arial,sans-serif",
    "Palatino Linotype": "Palatino Linotype,Georgia,serif",
};

const LIMITED_SUPPORT_FONTS = Object.fromEntries(
    Object.entries(WEB_SUPPORTED_FONTS)
        .concat(Object.entries(GOOGLE_FONTS))
        .sort(([fontA], [fontB]) => fontA.localeCompare(fontB))
);

export const FONT_FAMILIES = {
    mail: {
        families: EMAIL_SAFE_FONTS,
        label: _t("Email-safe fonts"),
        description: _t("Supported by most popular email clients"),
    },
    google: {
        families: LIMITED_SUPPORT_FONTS,
        label: _t("Limited-support fonts"),
        description: _t("A fallback font will be used for some email clients"),
    },
};

export class FontFamilyPicker extends BaseOptionComponent {
    static template = "mass_mailing.FontFamilyPicker";
    static components = {
        ...BaseOptionComponent.components,
        BuilderSelectLabel: MassMailingBuilderSelectLabel,
    };
    static props = {
        action: String,
        actionParam: Object,
        extraClass: { type: String, optional: true },
    };
    FONT_FAMILIES = FONT_FAMILIES;
}
