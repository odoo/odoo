import { BaseOptionComponent } from "@html_builder/core/utils";
import { CardImagePositionOption } from "./card_image_position_option";

export class CarouselCardsItemOption extends BaseOptionComponent {
    static template = "website.CarouselCardsItemOption";
    static selector = ".s_carousel_cards_item";
    static applyTo = ":scope > .s_carousel_cards_card";
    static components = {
        CardImagePositionOption,
    };
}
