import { BaseOptionComponent } from "@html_builder/core/utils";

export class ImageAndFaOption extends BaseOptionComponent {
    static template = "html_builder.ImageAndFaOption";
    static selector = "span.fa, i.fa, img";
    static name = "imageAndFaOption";
}
