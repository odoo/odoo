import { registry } from "@web/core/registry";
import { CardOption } from "./card_option";

export class CarouselMultipleItemOption extends CardOption {
    static id = "carousel_multiple_item_option";
    static template = "website.CarouselMultipleItemOption";
    static defaultProps = {
        disableWidth: true,
    };
}

registry.category("website-options").add(CarouselMultipleItemOption.id, CarouselMultipleItemOption);
