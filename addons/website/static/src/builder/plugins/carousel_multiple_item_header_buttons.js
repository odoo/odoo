import { useOperation } from "@html_builder/core/operation_plugin";
import { useDomState } from "@html_builder/core/utils";
import { Component } from "@odoo/owl";
import { getCarouselCenteringIndex } from "@website/utils/misc";

export class CarouselMultipleItemHeaderMiddleButtons extends Component {
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
                hasMultiItems: carouselItemsNumber > 1,
            };
        });
    }

    slide(direction) {
        const currentEl = this.env.getEditingElement().closest(".carousel-item");
        const carouselEl = currentEl.closest(".carousel");
        const slideEls = carouselEl.querySelectorAll(".carousel-item");
        const currentIndex = Array.from(slideEls).indexOf(currentEl);
        let newIndex;
        if (direction === "next") {
            newIndex = currentIndex + 1 < slideEls.length ? currentIndex + 1 : 0;
        } else {
            newIndex = currentIndex > 0 ? currentIndex - 1 : slideEls.length - 1;
        }
        const nextTargetElement = slideEls[newIndex];
        direction = getCarouselCenteringIndex(nextTargetElement) ?? 0;
        this.props.applyAction("slideCarouselMultiple", {
            editingElement: carouselEl,
            params: {
                direction,
                nextTargetElement,
            },
        });
    }

    addSlide() {
        this.callOperation(async () => {
            await this.props.addSlide(this.env.getEditingElement());
        });
    }

    removeSlide() {
        if (this.state.hasMultiItems) {
            this.callOperation(async () => {
                await this.props.removeSlide(this.env.getEditingElement());
            });
        }
    }
}
