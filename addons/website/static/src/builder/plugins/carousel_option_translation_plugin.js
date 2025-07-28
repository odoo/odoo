import { CarouselOptionPlugin } from "./carousel_option_plugin";

export class CarouselOptionTranslationPlugin extends CarouselOptionPlugin {
    static id = "carouselOption";
    static dependencies = ["builderOptions", "builderActions"];
}
