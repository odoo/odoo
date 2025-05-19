import { Component, useState } from "@odoo/owl";
import { useDomState } from "@html_builder/core/utils";
import { loadImageDataURL, getImageSizeFromCache } from "@html_editor/utils/image_processing";
import { KeepLast } from "@web/core/utils/concurrency";
import { getImageSrc } from "@html_editor/utils/image";

export class ImageSizeTag extends Component {
    static template = "website.ImageSizeTag";
    static props = {};
    setup() {
        this.keepLast = new KeepLast();
        this.state = useState({ size: 0 });
        useDomState((el) => this.updateImageSize(el));
        this.updateImageSize(this.env.getEditingElement());
    }

    async updateImageSize(el) {
        try {
            const src = getImageSrc(el);
            await this.keepLast.add(loadImageDataURL(src));
            this.state.size = Math.round((getImageSizeFromCache(src) / 1024) * 10) / 10;
        } catch {
            // skip
        }
    }
}
