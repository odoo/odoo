import { BaseOptionComponent } from "@html_builder/core/utils";

export class TranslateImageOption extends BaseOptionComponent {
    static template = "website.ImgTranslationOption";
    static selector = "img.o_savable_attribute";
    static editableOnly = false;
}

export class TranslateVideoOption extends BaseOptionComponent {
    static template = "website.VideoTranslationOption";
    static selector = ".media_iframe_video.o_savable_attribute";
    static editableOnly = false;
}

export class TranslateDocumentOption extends BaseOptionComponent {
    static template = "website.DocumentTranslationOption";
    static selector = ".o_file_box";
    static editableOnly = false;
}
