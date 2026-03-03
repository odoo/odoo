import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { getMimetypeBeforeShape } from "@html_builder/utils/image";
import { isImageSupportedForProcessing } from "@html_editor/main/media/image_post_process_plugin";
import { isWebGLEnabled } from "@html_editor/utils/image_processing";
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
            const canUseGlFilter = isWebGLEnabled();
            const mimetype = await getMimetypeBeforeShape(editingElement);
            const showFilter = await isImageSupportedForProcessing(editingElement, mimetype);
            return {
                isCustomFilter: editingElement.dataset.glFilter === "custom",
                showFilter,
                disableFilter: !canUseGlFilter,
                tooltip: !canUseGlFilter ? _t("WebGL is not enabled on your browser.") : undefined,
            };
        });
    }
}
