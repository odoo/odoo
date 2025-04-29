import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { shouldPreventGifTransformation } from "@html_editor/main/media/image_post_process_plugin";
import { loadImageInfo } from "@html_editor/utils/image_processing";
import { KeepLast } from "@web/core/utils/concurrency";

export class ImageFilterOption extends BaseOptionComponent {
    static template = "html_builder.ImageFilterOption";
    static props = {
        level: { type: Number, optional: true },
    };
    static defaultProps = {
        level: 0,
    };
    setup() {
        super.setup();
        const keepLast = new KeepLast();
        this.state = useDomState((editingElement) => {
            keepLast
                .add(
                    loadImageInfo(editingElement).then((data) => ({
                        ...editingElement.dataset,
                        ...data,
                    }))
                )
                .then((data) => {
                    this.state.showFilter =
                        data.mimetypeBeforeConversion && !shouldPreventGifTransformation(data);
                });
            return {
                isCustomFilter: editingElement.dataset.glFilter === "custom",
                showFilter: false,
            };
        });
    }
}
