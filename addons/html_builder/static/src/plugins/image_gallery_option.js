
import { useDomState, useIsActiveItem } from "@html_builder/core/building_blocks/utils";
import { defaultBuilderComponents } from "../core/default_builder_components";
import { Component } from "@odoo/owl";

export class ImageGalleryComponent extends Component {
    static template = "html_builder.ImageGalleryOption";
    static components = { ...defaultBuilderComponents };

    setup() {
        this.isActiveItem = useIsActiveItem();
        this.state = useDomState((editingElement) => ({
            isSlideShow: editingElement.classList.contains("o_slideshow"),
        }));
    }
}
