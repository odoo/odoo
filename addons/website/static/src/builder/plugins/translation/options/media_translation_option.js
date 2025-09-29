import { BaseOptionComponent } from "@html_builder/core/utils";

export class TranslateImageOption extends BaseOptionComponent {
    static template = "website.ImgTranslationOption";
    static selector = "img.o_savable_attribute";
    static editableOnly = false;
}
