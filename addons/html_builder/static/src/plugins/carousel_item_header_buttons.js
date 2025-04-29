import { useOperation } from "@html_builder/core/operation_plugin";
import { Component } from "@odoo/owl";

export class CarouselItemHeaderMiddleButtons extends Component {
    static template = "html_builder.CarouselItemHeaderMiddleButtons";
    static props = {
        slideCarousel: Function,
        addSlide: Function,
        removeSlide: Function,
    };

    setup() {
        this.callOperation = useOperation();
    }

    slidePrev() {
        this.callOperation(async () => {
            await this.props.slideCarousel("prev", this.env.getEditingElement());
        });
    }

    slideNext() {
        this.callOperation(async () => {
            await this.props.slideCarousel("next", this.env.getEditingElement());
        });
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
