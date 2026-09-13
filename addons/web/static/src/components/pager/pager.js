// @ts-check
/** @odoo-module native */

import { Component, useEffect, useState } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { PagerEvent } from "@web/core/events";
import { clamp } from "@web/core/utils/format/numbers";
import { useAutofocus } from "@web/core/utils/hooks";

const log = makeLogger("web.components.pager");

export class Pager extends Component {
    static template = "web.Pager";
    static defaultProps = {
        isEditable: true,
        withAccessKey: true,
    };
    static props = {
        offset: Number,
        limit: Number,
        total: Number,
        onUpdate: Function,
        isEditable: { type: Boolean, optional: true },
        withAccessKey: { type: Boolean, optional: true },
        updateTotal: { type: Function, optional: true },
    };

    /** @type {{ isEditing: boolean; isDisabled: boolean }} */
    state;
    /** @type {import("@odoo/owl").Ref<HTMLElement>} */
    inputRef;

    setup() {
        useLifecycleLog(log);
        this.state = useState({
            isEditing: false,
            isDisabled: false,
        });
        this.inputRef = useAutofocus();
        let firstMount = true;
        useEffect(
            () => {
                if (!firstMount && this.env.isSmall) {
                    this.env.bus.trigger(PagerEvent.UPDATED, {
                        value: this.value,
                        total: this.props.total,
                    });
                }
                firstMount = false;
            },
            () => [this.props.offset, this.props.limit, this.props.total],
        );
    }

    /** @returns {number} */
    get minimum() {
        return this.props.offset + 1;
    }
    /** @returns {number} */
    get maximum() {
        return Math.min(this.props.offset + this.props.limit, this.props.total);
    }
    /** @returns {string} */
    get value() {
        const parts = [this.minimum];
        if (this.props.limit > 1) {
            parts.push(this.maximum);
        }
        return parts.join("-");
    }
    /** @returns {boolean} */
    get isSinglePage() {
        return (
            !this.props.updateTotal &&
            this.minimum === 1 &&
            this.maximum === this.props.total
        );
    }
    /** @param {-1 | 1} direction */
    async navigate(direction) {
        if (this.state.isDisabled) {
            return;
        }
        let minimum = this.props.offset + this.props.limit * direction;
        let total = this.props.total;
        if (this.props.updateTotal && minimum < 0) {
            await this.whileDisabled(async () => {
                total = await this.props.updateTotal();
            });
        }
        if (minimum >= total) {
            if (!this.props.updateTotal) {
                minimum = 0;
            }
        } else if (minimum < 0 && this.props.limit === 1) {
            minimum = total - 1;
        } else if (minimum < 0 && this.props.limit > 1) {
            minimum = total - (total % this.props.limit || this.props.limit);
        }
        return this.update(minimum, this.props.limit, true);
    }
    /**
     * @param {string} value
     * @returns {{ minimum: number, maximum: number }}
     */
    parse(value) {
        const [minStr, maxStr] = value.trim().split(/\s*[-\s,;]\s*/);
        const minimum = Number.parseInt(minStr, 10);
        const maximum = maxStr ? Number.parseInt(maxStr, 10) : minimum;
        if (this.props.updateTotal) {
            return { minimum: Math.max(minimum - 1, 0), maximum: Math.max(maximum, 1) };
        }
        return {
            minimum: clamp(minimum, 1, this.props.total) - 1,
            maximum: clamp(maximum, 1, this.props.total),
        };
    }
    /** @param {string} value */
    async setValue(value) {
        const { minimum, maximum } = this.parse(value);

        if (!Number.isNaN(minimum) && !Number.isNaN(maximum) && minimum < maximum) {
            return this.update(minimum, maximum - minimum);
        }
        this.resetInput();
    }

    resetInput() {
        const el = /** @type {HTMLInputElement | null} */ (this.inputRef.el);
        if (el && el.value !== this.value) {
            el.value = this.value;
        }
    }
    /**
     * @param {number} offset
     * @param {number} limit
     * @param {boolean} [hasNavigated]
     */
    async update(offset, limit, hasNavigated) {
        log.logic("update", () => ({
            offset,
            limit,
            hasNavigated,
            total: this.props.total,
        }));
        await this.whileDisabled(async () => {
            try {
                await this.props.onUpdate({ offset, limit }, hasNavigated);
            } finally {
                this.state.isEditing = false;
            }
        });
    }

    async updateTotal() {
        await this.whileDisabled(() => this.props.updateTotal());
    }

    /** @param {() => Promise<any> | any} operation */
    async whileDisabled(operation) {
        if (this.state.isDisabled) {
            return;
        }
        this.state.isDisabled = true;
        try {
            await operation();
        } finally {
            this.state.isDisabled = false;
        }
    }

    stopEditing() {
        this.state.isEditing = false;
    }
    /** @param {Event} ev */
    onInputChange(ev) {
        this.setValue(/** @type {HTMLInputElement} */ (ev.target).value);
    }
    /** @param {KeyboardEvent} ev */
    onInputKeydown(ev) {
        switch (ev.key) {
            case "Enter":
                ev.preventDefault();
                ev.stopPropagation();
                this.setValue(/** @type {HTMLInputElement} */ (ev.currentTarget).value);
                break;
            case "Escape":
                ev.preventDefault();
                ev.stopPropagation();
                this.state.isEditing = false;
                break;
        }
    }
    onValueClick() {
        if (this.props.isEditable && !this.state.isEditing && !this.state.isDisabled) {
            this.state.isEditing = true;
        }
    }
}
