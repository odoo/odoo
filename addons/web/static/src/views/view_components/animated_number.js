import { browser } from "@web/core/browser/browser";
import { formatInteger, formatMonetary } from "@web/views/fields/formatters";

import { Component, onWillUnmount, onWillUpdateProps, useState } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { user } from "@web/core/user";
import { MultiCurrencyPopover } from "@web/views/view_components/multi_currency_popover";

export class AnimatedNumber extends Component {
    static template = "web.AnimatedNumber";
    static props = {
        value: Number,
        duration: Number,
        animationClass: { type: String, optional: true },
        currencies: { type: Array, optional: true },
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
        this.state = useState({ value: this.props.value });
        this.handle = null;
        this.multiCurrencyPopover = usePopover(MultiCurrencyPopover, {
            position: "right",
        });
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
        if (this.currencyId) {
            return formatMonetary(value, {
                currencyId: this.currencyId,
                humanReadable: true,
                digits: [null, 0],
                minDigits: 3,
            });
        }
        return formatInteger(value, { humanReadable: true, minDigits: 3 });
    }

    openMultiCurrencyPopover(ev) {
        if (!this.multiCurrencyPopover.isOpen) {
            this.multiCurrencyPopover.open(ev.target, {
                currencyIds: this.props.currencies,
                target: ev.target,
                value: this.props.value,
            });
        }
    }

    get currencyId() {
        const { currencies } = this.props;
        if (currencies?.length) {
            return currencies.length > 1 ? user.activeCompany.currency_id : currencies[0];
        }
        return false;
    }
}
