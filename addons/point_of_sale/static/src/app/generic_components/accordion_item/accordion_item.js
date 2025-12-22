import { Component, useState, useRef, useEffect, onMounted } from "@odoo/owl";

export class AccordionItem extends Component {
    static template = "pos_hr.AccordionItem";

    static props = {
        disabled: { type: Boolean, optional: true },
        slots: Object,
    };

    static defaultProps = {
        disabled: false,
    };

    setup() {
        this.content = useRef("content_container");
        this.state = useState({
            open: false,
        });
        onMounted(() => {
            this.contentHeight = this.calculateFullHeight();
        });
        useEffect(
            () => {
                this.contentHeight = this.calculateFullHeight();
            },
            () => [this.props.slots.content]
        );
    }

    toggle() {
        if (this.props.disabled) {
            return;
        }
        this.state.open = !this.state.open;
    }

    calculateFullHeight() {
        const children = Array.from(this.content.el.getElementsByClassName("accordion-content"));
        const fullHeight = children.reduce((accumulator, child) => {
            return accumulator + Math.min(this.getHiddenHeight(child), 100);
        }, 0);
        return fullHeight;
    }

    getHiddenHeight(el) {
        if (!el?.cloneNode) {
            return 0;
        }

        const clone = el.cloneNode(true);

        Object.assign(clone.style, {
            overflow: "visible",
            height: "auto",
            maxHeight: "none",
            opacity: "0",
            visibility: "hidden",
            display: "block",
        });

        el.after(clone);
        const height = clone.offsetHeight;
        clone.remove();

        return height;
    }
}
