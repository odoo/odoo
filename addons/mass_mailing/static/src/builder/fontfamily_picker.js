import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { MassMailingBuilderSelectLabel } from "./components/mass_mailing_builder_select_label";

export const MAIL_FONT_FAMILIES = {
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

const WEB_FONT_FAMILIES = {
    "Lucida Sans": "Lucida Sans,Lucida Grande,Verdana,sans-serif",
    "Palatino Linotype": "Palatino Linotype,Palatino,Book Antiqua,serif",
};

const GOOGLE_FONT_FAMILIES = {
    Inter: "Inter,Helvetica Neue,Arial,sans-serif",
    Comfortaa: "Comfortaa,Quicksand,Nunito,Verdana,sans-serif",
    Nunito: "Nunito,Comfortaa,Quicksand,Trebuchet MS,sans-serif",
    Quicksand: "Quicksand,Nunito,Comfortaa,Verdana,sans-serif",
    Dosis: "Dosis,Quicksand,Signika,Ubuntu,sans-serif",
    Signika: "Signika,Ubuntu,Dosis,Trebuchet MS,sans-serif",
    Ubuntu: "Ubuntu,Signika,Dosis,Trebuchet MS,sans-serif",
    Catamaran: "Catamaran,Helvetica Neue,Arial,sans-serif",
    Epilogue: "Epilogue,Helvetica Neue,Arial,sans-serif",
    Manrope: "Manrope,Helvetica Neue,Arial,sans-serif",
    Montserrat: "Montserrat,Helvetica Neue,Arial,sans-serif",
    Mukta: "Mukta,Noto Sans,Roboto,Arial,sans-serif",
    "Noto Sans": "Noto Sans,Arial,Helvetica Neue,sans-serif",
    Poppins: "Poppins,Helvetica Neue,Arial,sans-serif",
    Rubik: "Rubik,Helvetica Neue,Arial,sans-serif",
    "DM Sans": "DM Sans,Helvetica Neue,Arial,sans-serif",
    "Fira Sans": "Fira Sans,Open Sans,Arial,sans-serif",
    Mulish: "Mulish,Open Sans,Roboto,Arial,sans-serif",
    "Open Sans": "Open Sans,Fira Sans,Helvetica Neue,Arial,sans-serif",
    Roboto: "Roboto,Helvetica Neue,Arial,sans-serif",
    "Source Sans Pro": "Source Sans Pro,Open Sans,Roboto,Arial,sans-serif",
    Anton: "Anton,Impact,Arial Black,sans-serif",
    "Barlow Condensed": "Barlow Condensed,Oswald,Arial Narrow,Arial,sans-serif",
    Karla: "Karla,Lato,Arial,sans-serif",
    Lato: "Lato,Karla,Helvetica Neue,Arial,sans-serif",
    Oswald: "Oswald,Barlow Condensed,Arial Narrow,Arial,sans-serif",
    Raleway: "Raleway,Lato,Helvetica Neue,Arial,sans-serif",
    Cabin: "Cabin,Open Sans,Lato,Arial,sans-serif",
    "Josefin Sans": "Josefin Sans,Raleway,Montserrat,Arial,sans-serif",
    Merriweather: "Merriweather,Georgia,Times New Roman,serif",
    Aleo: "Aleo,Merriweather,Georgia,serif",
    "Playfair Display": "Playfair Display,Times New Roman,Georgia,serif",
    "Space Mono": "Space Mono,Courier New,Lucida Console,monospace",
    "Amatic SC": "Amatic SC,Segoe Print,Comic Sans MS,cursive",
};

const FONT_FAMILIES = {
    "Mail Fonts": MAIL_FONT_FAMILIES,
    "Web Fonts": WEB_FONT_FAMILIES,
    "Google Fonts": GOOGLE_FONT_FAMILIES,
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
