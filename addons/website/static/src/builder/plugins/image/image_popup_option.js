import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { allowedToCreateLink } from "@html_editor/main/link/link_plugin";
import { registry } from "@web/core/registry";

export class ImagePopUpOption extends BaseOptionComponent {
    static id = "image_pop_up_option";
    static template = "website.ImagePopUpOption";
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            available: allowedToCreateLink(editingElement),
        }));
    }
}

registry.category("builder-options").add(ImagePopUpOption.id, ImagePopUpOption);
