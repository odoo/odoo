import { BaseOptionComponent } from "@html_builder/core/utils";

export const FONT_FAMILIES = {
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

export class FontFamilyPicker extends BaseOptionComponent {
    static template = "mass_mailing.FontFamilyPicker";
    static props = {
        action: String,
        actionParam: Object,
        extraClass: { type: String, optional: true },
    };
    FONT_FAMILIES = FONT_FAMILIES;
}
