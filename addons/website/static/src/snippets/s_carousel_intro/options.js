import options from "@web_editor/js/editor/snippets.options";
import "@website/js/editor/snippets.options";

options.registry.CarouselIntro = options.registry.Carousel.extend({
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        // Prevent the "Controllers" option from being "centered" when
        // arrows and indicators are displayed.
        if (methodName === "selectClass" && params.name === "carousel_controllers_centered_opt") {
            const controllersEl = this.$target[0];
            const carouselEl = controllersEl.closest(".carousel");
            const indicatorsEl = controllersEl.querySelector(".carousel-indicators");
            if (
                !carouselEl.classList.contains("s_carousel_arrows_hidden")
                && !indicatorsEl.classList.contains("s_carousel_indicators_hidden")
            )
            {
                controllersEl.classList.toggle("justify-content-center");
                controllersEl.classList.toggle("justify-content-between");
            }
        }
        return this._super(...arguments);
    },
});
