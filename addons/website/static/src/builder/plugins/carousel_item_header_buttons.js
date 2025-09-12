import { useOperation } from "@html_builder/core/operation_plugin";
import { useDomState } from "@html_builder/core/utils";
import { Component } from "@odoo/owl";

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
        const applySpec = {
            editingElement: this.env.getEditingElement().closest(".carousel"),
            params: {
                direction: direction,
            },
        };

        this.props.applyAction("slideCarousel", applySpec);
    }

    addSlide() {
        const carouselEl = this.env.getEditingElement().closest(".carousel");

        this.callOperation(async () => {
            await this.props.addSlide(carouselEl);
        });
    }

    removeSlide() {
        this.callOperation(async () => {
            await this.props.removeSlide(this.env.getEditingElement());
        });
    }
}
