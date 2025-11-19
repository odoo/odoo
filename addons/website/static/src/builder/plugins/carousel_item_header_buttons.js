import { useOperation } from "@html_builder/core/operation_plugin";
import { useDomState } from "@html_builder/core/utils";
import { Component } from "@odoo/owl";
import { getCarouselCenteringIndex } from "@website/utils/misc";

export class CarouselItemHeaderMiddleButtons extends Component {
    static template = "website.CarouselItemHeaderMiddleButtons";
    static props = {
        applyAction: Function,
        addSlide: Function,
        removeSlide: Function,
    };

    setup() {
        this.callOperation = useOperation();
        this.state = useDomState((editingElement) => {
            const carouselItemsNumber = editingElement.parentElement.children.length;
            return {
                disableRemove: carouselItemsNumber === 1,
            };
        });
    }

    slide(direction) {
        const currentEl = this.env.getEditingElement().closest(".carousel-item");
        const carouselEl = currentEl.closest(".carousel");
        const isMultipleCarousel = carouselEl.classList.contains("s_carousel_multiple");
        let nextTargetElement;
        if (isMultipleCarousel) {
            const slideEls = carouselEl.querySelectorAll(".carousel-item:not(.carousel-item_copy)");
            const currentIndex = Array.from(slideEls).indexOf(currentEl);
            let newIndex;
            if (direction === "next") {
                newIndex = currentIndex + 1 < slideEls.length ? currentIndex + 1 : 0;
            } else {
                newIndex = currentIndex > 0 ? currentIndex - 1 : slideEls.length - 1;
            }
            nextTargetElement = slideEls[newIndex];
            direction = getCarouselCenteringIndex(nextTargetElement) ?? direction;
        }
        const applySpec = {
            editingElement: carouselEl,
            params: {
                direction: direction,
                nextTargetElement,
            },
        };

        this.props.applyAction("slideCarousel", applySpec);
    }

    addSlide() {
        this.callOperation(async () => {
            await this.props.addSlide(this.env.getEditingElement());
        });
    }

    removeSlide() {
        this.callOperation(async () => {
            await this.props.removeSlide(this.env.getEditingElement());
        });
    }
}
