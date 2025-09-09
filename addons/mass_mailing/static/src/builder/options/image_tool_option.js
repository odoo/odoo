import { useDomState } from "@html_builder/core/utils";
import { ImageToolOption } from "@html_builder/plugins/image/image_tool_option";

export class MassMailingImageToolOption extends ImageToolOption {
    static template = "mass_mailing.ImageToolOption";
    setup() {
        super.setup();
        this.massMailingState = useDomState((editingElement) => ({
            isImgFluid: editingElement.classList.contains("img-fluid"),
        }));
    }
}
