import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { MediaSizeOption } from "./media_size_option";
import { registry } from "@web/core/registry";

export class VideoSizeOption extends BaseOptionComponent {
    static id = "video_size_option";
    static template = "html_builder.VideoSizeOption";
    static components = { MediaSizeOption };

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isGridMode: editingElement.closest(".o_grid_mode, .o_grid"),
        }));
    }
}

registry.category("builder-options").add(VideoSizeOption.id, VideoSizeOption);
