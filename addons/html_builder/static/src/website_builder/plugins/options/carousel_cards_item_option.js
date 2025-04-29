import { BaseOptionComponent } from "@html_builder/core/utils";
import { UpdateOptionOnImgChanged } from "@html_builder/core/utils/update_on_img_changed";
import { CardImageAlignmentOption } from "./card_image_alignment_option";

export class CarouselCardsItemOption extends BaseOptionComponent {
    static template = "html_builder.CarouselCardsItemOption";
    static components = {
        CardImageAlignmentOption,
        UpdateOptionOnImgChanged,
    };
    static props = {};
}
