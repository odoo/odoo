import { BaseOptionComponent } from "@html_builder/core/utils";

export class MediaSizeOption extends BaseOptionComponent {
    static template = "html_builder.MediaSizeOption";
    static props = {
        level: { type: Number, optional: true },
    };
    static defaultProps = {
        level: 0,
    };
}
