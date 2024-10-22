import options from "@web_editor/js/editor/snippets.options";
import "@website/js/editor/snippets.options";

options.registry.CarouselBottomControllers = options.registry.Carousel.extend({
    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------
    /**
     * Add a custom class if all controllers are hidden.
     */
    toggleControllers() {
        const carouselEl = this.$target[0].closest(".carousel");
        const indicatorsWrapEl = carouselEl.querySelector(".carousel-indicators");
        if(
            carouselEl.classList.contains("s_carousel_arrows_hidden") &&
            indicatorsWrapEl.classList.contains("s_carousel_indicators_hidden")
        ) {
            carouselEl.classList.add("s_carousel_controllers_hidden");
        } else {
            carouselEl.classList.remove("s_carousel_controllers_hidden");
        }
    },
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
