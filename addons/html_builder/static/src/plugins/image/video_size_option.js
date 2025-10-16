import { BaseOptionComponent } from "@html_builder/core/utils";

export class VideoSizeOption extends BaseOptionComponent {
    static template = "html_builder.MediaSizeOption";
    static selector = ".media_iframe_video";
    static name = "videoSizeOption";
}
