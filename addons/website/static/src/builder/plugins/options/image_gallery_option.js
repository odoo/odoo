import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";

export class ImageGalleryComponent extends BaseOptionComponent {
    static template = "website.ImageGalleryOption";
    static selector = ".s_image_gallery";

    static components = { BorderConfigurator };

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isSlideShow: editingElement.classList.contains("o_slideshow"),
        }));
    }
}
