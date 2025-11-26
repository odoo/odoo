import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { CardImagePositionOption } from "./card_image_position_option";

export class CarouselCardsItemOption extends BaseOptionComponent {
    static id = "carousel_cards_item_option";
    static template = "website.CarouselCardsItemOption";
    static components = {
        CardImagePositionOption,
    };
}

registry.category("builder-options").add(CarouselCardsItemOption.id, CarouselCardsItemOption);
