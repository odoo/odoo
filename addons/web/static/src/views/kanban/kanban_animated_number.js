/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component, hooks } = owl;
const { onWillUpdateProps, onWillUnmount, useState } = hooks;

export class KanbanAnimatedNumber extends Component {
    setup() {
        this.formatInteger = registry.category("formatters").get("integer");
        this.state = useState({ value: this.props.value });
        this.handle = null;
        onWillUpdateProps((nextProps) => {
            const { value: from } = this.props;
            const { value: to, duration } = nextProps;
            if (!duration || to <= from) {
                this.state.value = to;
                return;
            }
            const startTime = Date.now();
            const animate = () => {
                const progress = (Date.now() - startTime) / duration;
                if (progress >= 1) {
                    this.state.value = to;
                } else {
                    this.state.value = from + (to - from) * progress;
                    this.handle = requestAnimationFrame(animate);
                }
            };
            cancelAnimationFrame(this.handle);
            animate();
        });
        onWillUnmount(() => cancelAnimationFrame(this.handle));
    }

    format(value) {
        return this.formatInteger(value, { humanReadable: true, decimals: 0, minDigits: 3 });
    }
}

KanbanAnimatedNumber.template = "web.KanbanAnimatedNumber";
KanbanAnimatedNumber.props = {
    value: Number,
    duration: Number,
    animationClass: { type: String, optional: true },
    currency: { type: [Object, false], optional: true },
    title: { type: String, optional: true },
};
