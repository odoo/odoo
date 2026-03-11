import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { CardImagePositionOption } from "./card_image_position_option";

export class CardImageOption extends BaseOptionComponent {
    static template = "website.CardImageOption";
    static components = { CardImagePositionOption };

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            hasCoverImage: !!editingElement.querySelector(":scope > .o_card_img_wrapper"),
        }));
    }
}
