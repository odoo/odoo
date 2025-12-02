import { useDomState } from "@html_builder/core/utils";
import { ImageToolOption } from "@html_builder/plugins/image/image_tool_option";
import { registry } from "@web/core/registry";

export class MassMailingImageToolOption extends ImageToolOption {
    static id = "mass_mailing_image_tool_option";
    static template = "mass_mailing.ImageToolOption";
    setup() {
        super.setup();
        this.massMailingState = useDomState((editingElement) => ({
            isImgFluid: editingElement.classList.contains("img-fluid"),
        }));
    }
}

registry.category("builder-options").add(MassMailingImageToolOption.id, MassMailingImageToolOption);
