import { CardOption } from "./card_option";

export class CarouselMultipleItemOption extends CardOption {
    static template = "website.CarouselMultipleItemOption";
    static selector = ".s_carousel_multiple_item";
    static applyTo = ":scope > .s_carousel_multiple_card";
    static defaultProps = {
        disableWidth: true,
    };
}
