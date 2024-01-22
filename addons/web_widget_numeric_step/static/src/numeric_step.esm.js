/** @odoo-module */

import {registry} from "@web/core/registry";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {_lt} from "@web/core/l10n/translation";
import {FloatField} from "@web/views/fields/float/float_field";
import {hasTouch} from "@web/core/browser/feature_detection";

export class NumericStep extends FloatField {
    setup() {
        super.setup();
    }
    _onStepClick(ev) {
        const $el = $(ev.target).parent().parent().find("input");
        if (!hasTouch()) {
            $el.focus();
        }
        const mode = $(ev.target).data("mode");
        this._doStep(mode);
    }
    _onKeyDown(ev) {
        if (ev.keyCode === $.ui.keyCode.UP) {
            this._doStep("plus");
        } else if (ev.keyCode === $.ui.keyCode.DOWN) {
            this._doStep("minus");
        }
    }
    _onWheel(ev) {
        ev.preventDefault();
        if (ev.deltaY > 0) {
            this._doStep("minus");
        } else {
            this._doStep("plus");
        }
    }
    updateField(val) {
        return Promise.resolve(this.props.update(val));
    }
    _doStep(mode) {
        let cval = this.props.value;
        if (mode === "plus") {
            cval += this.props.step;
        } else if (mode === "minus") {
            cval -= this.props.step;
        }
        if (cval < this.props.min) {
            cval = this.props.min;
        } else if (cval > this.props.max) {
            cval = this.props.max;
        }
        this.updateField(cval);
        this.props.setDirty(this._isSetDirty(cval));
        this.props.setDirty(false);
    }
    _isSetDirty(val) {
        return this.props.value != val;
    }
}

NumericStep.template = "web_widget_numeric_step";
NumericStep.props = {
    ...standardFieldProps,
    inputType: {type: String, optional: true},
    step: {type: Number, optional: true},
    min: {type: Number, optional: true},
    max: {type: Number, optional: true},
    placeholder: {type: String, optional: true},
};

NumericStep.displayName = _lt("Numeric Step");
NumericStep.supportedTypes = ["float"];
NumericStep.defaultProps = {
    inputType: "text",
};
NumericStep.extractProps = ({attrs}) => {
    return {
        name: attrs.name,
        inputType: attrs.options.type,
        step: attrs.options.step || 1,
        min: attrs.options.min,
        max: attrs.options.max,
        placeholder: attrs.options.placeholder,
    };
};

registry.category("fields").add("numeric_step", NumericStep);
