import { registry } from "@web/core/registry";
import { CarouselOptionPlugin } from "../../carousel_option_plugin";

export class CarouselOptionTranslationPlugin extends CarouselOptionPlugin {
    static id = "carouselOption";
    static dependencies = ["builderOptions", "builderActions"];
}

registry
    .category("translation-plugins")
    .add(CarouselOptionTranslationPlugin.id, CarouselOptionTranslationPlugin);
