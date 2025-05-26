import { useOperation } from "@html_builder/core/operation_plugin";
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
