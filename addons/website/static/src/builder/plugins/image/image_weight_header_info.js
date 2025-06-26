import { Component, useState } from "@odoo/owl";
import { useDomState } from "@html_builder/core/utils";
import { loadImageDataURL, getImageSizeFromCache } from "@html_editor/utils/image_processing";

export class ImageWeightHeaderInfo extends Component {
    static template = "website.ImageWeightHeaderInfo";
    static props = {
        isImageSupportedForProcessing: Function,
    };

    setup() {
        this.state = useState({
            weight: "",
        });
        useDomState(async (imgEl) => {
            try {
                await loadImageDataURL(imgEl.src);
                const size = getImageSizeFromCache(imgEl.src);
                this.state.weight = size ? `${(size / 1024).toFixed(1)} kb` : "";
            } catch (error) {
                if (error) {
                    this.state.weight = "";
                }
            }
            return {
                // Not actually used because of async.
            };
        });
    }
}
