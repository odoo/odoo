import options from "@web_editor/js/editor/snippets.options";
import "@website/js/editor/snippets.options";

options.registry.CarouselIntro = options.registry.Carousel.extend({
    /**
     * @override
     */
    async selectClass(previewMode, widgetValue, params) {
        // Prevent the "Controllers" option from being "centered" when
        // arrows and indicators are displayed
        await this._super(...arguments);
        const isArrowsOption = [
            "s_carousel_default",
            "s_carousel_boxed",
            "s_carousel_rounded",
            "s_carousel_arrows_hidden",
        ].includes(widgetValue);
        const isIndicatorsOption = params.applyTo === ".carousel-indicators";
        if (isIndicatorsOption || isArrowsOption) {
            const carouselEl = this.$target[0].closest(".carousel");
            const controllersEl = carouselEl.querySelector(".s_carousel_intro_controllers_row");
            const indicatorsEl = carouselEl.querySelector(".carousel-indicators");
            const hasHiddenArrows = carouselEl.classList.contains("s_carousel_arrows_hidden");
            const hasHiddenIndicators = indicatorsEl.classList.contains(
                "s_carousel_indicators_hidden"
            );
            let contentBetween = !hasHiddenIndicators && !hasHiddenArrows;
            const widget = this._requestUserValueWidgets("carousel_controllers_centered_opt");
            if (!contentBetween && widget[0]._value !== "justify-content-center") {
                contentBetween = true;
            }
            controllersEl.classList.toggle("justify-content-center", !contentBetween);
            controllersEl.classList.toggle("justify-content-between", contentBetween);
        }
    },
});
