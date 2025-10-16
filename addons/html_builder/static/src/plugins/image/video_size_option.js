import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { MediaSizeOption } from "./media_size_option";

export class VideoSizeOption extends BaseOptionComponent {
    static template = "html_builder.VideoSizeOption";
    static components = { MediaSizeOption };
    static selector = ".media_iframe_video";
    static name = "videoSizeOption";
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isGridMode: editingElement.closest(".o_grid_mode, .o_grid"),
        }));
    }
}
