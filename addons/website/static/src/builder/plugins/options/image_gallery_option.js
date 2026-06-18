import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { WebsiteBorderConfigurator } from "@website/builder/plugins/options/website_border_configurator_option";

export class ImageGalleryOption extends BaseOptionComponent {
    static id = "image_gallery_option";
    static template = "website.ImageGalleryOption";
    static components = {
        WebsiteBorderConfigurator,
    };

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isSlideShow: editingElement.classList.contains("o_slideshow"),
        }));
    }
}

registry.category("website-options").add(ImageGalleryOption.id, ImageGalleryOption);
