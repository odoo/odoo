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

    async doOperation(fn) {
        try {
            this.state.isTransitioning = true;
            await fn();
        } finally {
            this.state.isTransitioning = false;
        }
    }

    async slide(direction) {
        const applySpec = {
            editingElement: this.env.getEditingElement().closest(".carousel"),
            params: {
                direction: direction,
            },
        };
        this.doOperation(async () => this.props.applyAction("slideCarousel", applySpec));
    }

    addSlide() {
        const carouselEl = this.env.getEditingElement().closest(".carousel");
        this.doOperation(async () =>
            this.callOperation(async () => this.props.addSlide(carouselEl))
        );
    }

    removeSlide() {
        this.doOperation(async () =>
            this.callOperation(async () => this.props.removeSlide(this.env.getEditingElement()))
        );
    }
}
