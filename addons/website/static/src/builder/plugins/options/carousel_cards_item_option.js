import { BaseOptionComponent } from "@html_builder/core/utils";
import { CardImagePositionOption } from "./card_image_position_option";

export class CarouselCardsItemOption extends BaseOptionComponent {
    static template = "website.CarouselCardsItemOption";
    static components = {
        CardImagePositionOption,
    };
    static props = {};
}
