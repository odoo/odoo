import { BaseOptionComponent } from "@html_builder/core/utils";
import { CardImageAlignmentOption } from "./card_image_alignment_option";

export class CarouselCardsItemOption extends BaseOptionComponent {
    static template = "html_builder.CarouselCardsItemOption";
    static components = {
        CardImageAlignmentOption,
    };
    static props = {};
}
