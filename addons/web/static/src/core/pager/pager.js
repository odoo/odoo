/** @odoo-module **/

import { useAutofocus } from "../utils/hooks";

const { Component, useExternalListener, useState } = owl;

/**
 * Pager
 *
 * The pager goes from 1 to total (included).
 * The current value is minimum if limit === 1 or the interval:
 *      [minimum, minimum + limit[ if limit > 1].
 * The value can be manually changed by clicking on the pager value and giving
 * an input matching the pattern: min[,max] (in which the comma can be a dash
 * or a semicolon).
 * The pager also provides two buttons to quickly change the current page (next
 * or previous).
 * @extends Component
 */
export class Pager extends Component {
    setup() {
        this.state = useState({
            isEditing: false,
            isDisabled: false,
        });
        this.inputRef = useAutofocus();
        useExternalListener(document, "mousedown", this.onClickAway, { capture: true });
    }

    /**
     * @returns {number}
     */
    get minimum() {
        return this.props.offset + 1;
    }
    /**
     * @returns {number}
     */
    get maximum() {
        return Math.min(this.props.offset + this.props.limit, this.props.total);
    }
    /**
     * @returns {string}
     */
    get value() {
        const parts = [this.minimum];
        if (this.props.limit > 1) {
            parts.push(this.maximum);
        }
        return parts.join("-");
    }
    /**
     * @returns {boolean} true if there is only one page
     */
    get isSinglePage() {
        return this.minimum === 1 && this.maximum === this.props.total;
    }

    /**
     * @param {-1 | 1} direction
     */
    navigate(direction) {
        let minimum = this.props.offset + this.props.limit * direction;
        if (minimum >= this.props.total) {
            minimum = 0;
        } else if (minimum < 0 && this.props.limit === 1) {
            minimum = this.props.total - 1;
        } else if (minimum < 0 && this.props.limit > 1) {
            minimum = this.props.total - (this.props.total % this.props.limit || this.props.limit);
        }
        this.update(minimum, this.props.limit, true);
    }
    /**
     * @param {string} value
     * @returns {{ minimum: number, maximum: number }}
     */
    parse(value) {
        let [minimum, maximum] = value.trim().split(/\s*[-\s,;]\s*/);
        const clamp = (value) => Math.min(Math.max(value, 1), this.props.total);
        return {
            minimum: clamp(parseInt(minimum, 10)) - 1,
            maximum: clamp(maximum ? parseInt(maximum, 10) : minimum),
        };
    }
    /**
     * @param {string} value
     */
    setValue(value) {
        const { minimum, maximum } = this.parse(value);

        if (!isNaN(minimum) && !isNaN(maximum) && minimum < maximum) {
            this.update(minimum, maximum - minimum);
        }
    }
    /**
     * @param {number} offset
     * @param {number} limit
     * @param {Boolean} hasNavigated
     */
    async update(offset, limit, hasNavigated) {
        this.state.isDisabled = true;
        await this.props.onUpdate({ offset, limit }, hasNavigated);
        this.state.isDisabled = false;
        this.state.isEditing = false;
    }

    /**
     * @param {MouseEvent} ev
     */
    onClickAway(ev) {
        if (ev.target !== this.inputRef.el) {
            this.state.isEditing = false;
        }
    }
    onInputBlur() {
        this.state.isEditing = false;
    }
    /**
     * @param {Event} ev
     */
    onInputChange(ev) {
        this.setValue(ev.target.value);
        if (!this.state.isDisabled) {
            ev.preventDefault();
        }
    }
    /**
     * @param {KeyboardEvent} ev
     */
    onInputKeydown(ev) {
        switch (ev.key) {
            case "Enter":
                ev.preventDefault();
                ev.stopPropagation();
                this.setValue(ev.currentTarget.value);
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
            if (this.inputRef.el) {
                this.inputRef.el.focus();
            }
            this.state.isEditing = true;
        }
    }
}
Pager.template = "web.Pager";

Pager.defaultProps = {
    isEditable: true,
    withAccessKey: true,
};
Pager.props = {
    offset: Number,
    limit: Number,
    total: Number,
    onUpdate: Function,
    isEditable: { type: Boolean, optional: true },
    withAccessKey: { type: Boolean, optional: true },
};
