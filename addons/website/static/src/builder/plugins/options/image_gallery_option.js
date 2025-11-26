import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class ImageGalleryOption extends BaseOptionComponent {
    static id = "image_gallery_option";
    static template = "website.ImageGalleryOption";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isSlideShow: editingElement.classList.contains("o_slideshow"),
        }));
    }
}

registry.category("builder-options").add(ImageGalleryOption.id, ImageGalleryOption);
