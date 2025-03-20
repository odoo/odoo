import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class ImageGalleryComponent extends BaseOptionComponent {
    static template = "html_builder.ImageGalleryOption";
    static props = {};

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isSlideShow: editingElement.classList.contains("o_slideshow"),
        }));
    }
}
