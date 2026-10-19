import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class CarouselOption extends BaseOptionComponent {
    static id = "carousel_option";
    static template = "website.CarouselOption";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            // Compatibility before .o_carousel_pause button.
            hasPauseButton: !!editingElement.querySelector(".o_carousel_pause"),
        }));
    }
}

export class CarouselBottomControllersOption extends CarouselOption {
    static id = "carousel_bottom_controllers_option";
    static template = "website.CarouselBottomControllersOption";
}

export class CarouselCardsOption extends CarouselOption {
    static id = "carousel_cards_option";
    static template = "website.CarouselCardsOption";
}

registry.category("website-options").add(CarouselOption.id, CarouselOption);
registry
    .category("website-options")
    .add(CarouselBottomControllersOption.id, CarouselBottomControllersOption);
registry.category("website-options").add(CarouselCardsOption.id, CarouselCardsOption);
