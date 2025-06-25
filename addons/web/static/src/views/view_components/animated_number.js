import { browser } from "@web/core/browser/browser";
import { formatInteger } from "@web/views/fields/formatters";

import { Component, onWillUpdateProps, onWillUnmount, useState } from "@odoo/owl";

export class AnimatedNumber extends Component {
    static template = "web.AnimatedNumber";
    static props = {
        value: Number,
        duration: Number,
        animationClass: { type: String, optional: true },
        currency: { type: [Object, Boolean], optional: true },
        title: { type: String, optional: true },
        slots: {
            type: Object,
            shape: {
                prefix: { type: Object, optional: true },
            },
            optional: true,
        },
    };
    static enableAnimations = true;

    setup() {
        this.formatInteger = formatInteger;
        this.state = useState({ value: this.props.value });
        this.handle = null;
        onWillUpdateProps((nextProps) => {
            const { value: from } = this.props;
            const { value: to, duration } = nextProps;
            if (!this.constructor.enableAnimations || !duration || to <= from) {
                browser.cancelAnimationFrame(this.handle);
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
                    this.handle = browser.requestAnimationFrame(animate);
                }
            };
            browser.cancelAnimationFrame(this.handle);
            animate();
        });
        onWillUnmount(() => browser.cancelAnimationFrame(this.handle));
    }

    format(value) {
        return this.formatInteger(value, { humanReadable: true, decimals: 0, minDigits: 3 });
    }
}
