import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { shouldPreventGifTransformation } from "@html_editor/main/media/image_post_process_plugin";
import { loadImageInfo, isWebGLEnabled } from "@html_editor/utils/image_processing";
import { _t } from "@web/core/l10n/translation";

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
        this.state = useDomState(async (editingElement) => {
            const data = await loadImageInfo(editingElement).then((data) => ({
                ...editingElement.dataset,
                ...data,
            }));
            const canUseGlFilter = isWebGLEnabled();
            return {
                isCustomFilter: editingElement.dataset.glFilter === "custom",
                showFilter: data.mimetypeBeforeConversion && !shouldPreventGifTransformation(data),
                disableFilter: !canUseGlFilter,
                tooltip: !canUseGlFilter ? _t("WebGL is not enabled on your browser.") : undefined,
            };
        });
    }
}
