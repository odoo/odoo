import { BaseOptionComponent } from "@html_builder/core/utils";
import { CardImageAlignmentOption } from "./card_image_alignment_option";

export class CarouselCardsItemOption extends BaseOptionComponent {
    static template = "website.CarouselCardsItemOption";
    static components = {
        CardImageAlignmentOption,
    };
    static props = {};
}
