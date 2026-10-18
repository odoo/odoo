import { useOperation } from "@html_builder/core/operation_plugin";
import { useDomState } from "@html_builder/core/utils";
import { Component, useState } from "@odoo/owl";

export class CarouselItemHeaderMiddleButtons extends Component {
    static template = "website.CarouselItemHeaderMiddleButtons";
    static props = {
        applyAction: Function,
        addSlide: Function,
        removeSlide: Function,
    };

    setup() {
        this.callOperation = useOperation();
        this.state = useState({
            isTransitioning: false,
        });
        this.domState = useDomState((editingElement) => {
            const carouselItemsNumber = editingElement.parentElement.children.length;
            return {
                hasMultiItems: carouselItemsNumber > 1,
            };
        });
    }

    async slide(direction) {
        this.state.isTransitioning = true;
        const applySpec = {
            editingElement: this.env.getEditingElement().closest(".carousel"),
            params: {
                direction: direction,
            },
        };

        await this.props.applyAction("slideCarousel", applySpec);
        this.state.isTransitioning = false;
    }

    addSlide() {
        this.state.isTransitioning = true;
        const carouselEl = this.env.getEditingElement().closest(".carousel");

        this.callOperation(async () => {
            await this.props.addSlide(carouselEl);
            this.state.isTransitioning = false;
        });
    }

    removeSlide() {
        this.state.isTransitioning = true;
        this.callOperation(async () => {
            await this.props.removeSlide(this.env.getEditingElement());
            this.state.isTransitioning = false;
        });
    }
}
