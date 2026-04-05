/** @odoo-module **/

import {
    Component,
    onMounted,
    onWillUpdateProps,
    status,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { nextId } from "@odx_owl/core/utils/ids";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function roundToStep(value, step, min) {
    if (!step || step <= 0) {
        return value;
    }
    return Number((Math.round((value - min) / step) * step + min).toFixed(5));
}

function normalizeSliderValues(value, min, max) {
    const array = Array.isArray(value) ? value : value !== undefined ? [value] : [min];
    const normalized = array
        .map((item) => clamp(Number(item) || 0, min, max))
        .sort((left, right) => left - right);
    return normalized.length ? normalized : [min];
}

export class Slider extends Component {
    static template = "odx_owl.Slider";
    static props = {
        ariaLabel: { type: String, optional: true },
        ariaValueText: { optional: true, validate: () => true },
        className: { type: String, optional: true },
        defaultValue: { optional: true, validate: () => true },
        disabled: { type: Boolean, optional: true },
        dir: { type: String, optional: true },
        max: { type: Number, optional: true },
        min: { type: Number, optional: true },
        minStepsBetweenThumbs: { type: Number, optional: true },
        name: { type: String, optional: true },
        onValueChange: { type: Function, optional: true },
        onValueCommit: { type: Function, optional: true },
        orientation: { type: String, optional: true },
        step: { type: Number, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
        max: 100,
        min: 0,
        minStepsBetweenThumbs: 0,
        orientation: "horizontal",
        step: 1,
    };

    setup() {
        this.pendingRender = false;
        this.rootRef = useRef("rootRef");
        this.trackRef = useRef("trackRef");
        this.handleTrackPointerDown = (ev) => this.onTrackPointerDown(ev);
        this.handleThumbPointerDown = (index, ev) => this.startDrag(index, ev);
        this.handleThumbKeydown = (index, ev) => this.onThumbKeydown(index, ev);
        this.state = useState({
            activeThumbIndex: null,
            dragging: false,
            id: nextId("odx-slider"),
            values: normalizeSliderValues(
                this.props.value ?? this.props.defaultValue,
                this.minimumValue,
                this.maximumValue
            ),
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.value !== undefined) {
                this.state.values = normalizeSliderValues(
                    nextProps.value,
                    nextProps.min ?? this.minimumValue,
                    nextProps.max ?? this.maximumValue
                );
            }
        });

        onMounted(() => {
            if (this.pendingRender) {
                this.pendingRender = false;
                this.render(true);
            }
        });

        useExternalListener(window, "pointermove", (ev) => this.onPointerMove(ev));
        useExternalListener(window, "pointerup", () => this.endDrag());
        useExternalListener(window, "pointercancel", () => this.endDrag());
    }

    get minimumValue() {
        return Number(this.props.min) || 0;
    }

    get maximumValue() {
        return Number(this.props.max) || 100;
    }

    get currentValues() {
        return this.props.value !== undefined
            ? normalizeSliderValues(this.props.value, this.minimumValue, this.maximumValue)
            : this.state.values;
    }

    get classes() {
        return cn(
            "odx-slider",
            {
                "odx-slider--vertical": this.props.orientation === "vertical",
                "odx-slider--horizontal": this.props.orientation !== "vertical",
            },
            this.props.className
        );
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get isRtl() {
        return this.props.orientation !== "vertical" && isRtlDirection(this.direction);
    }

    get rangeStyle() {
        const values = this.currentValues;
        const start = values.length > 1 ? this.valueToPercent(values[0]) : 0;
        const end = this.valueToPercent(values[values.length - 1]);
        if (this.props.orientation === "vertical") {
            return `bottom: ${start}%; height: ${end - start}%;`;
        }
        return `${this.isRtl ? "right" : "left"}: ${start}%; width: ${end - start}%;`;
    }

    getHiddenInputName(index) {
        return this.currentValues.length > 1 ? `${this.props.name || ""}[${index}]` : this.props.name;
    }

    get minimumDistance() {
        return Math.max(0, Number(this.props.minStepsBetweenThumbs) || 0) * (Number(this.props.step) || 0);
    }

    getThumbStyle(value) {
        const percent = this.valueToPercent(value);
        return this.props.orientation === "vertical"
            ? `bottom: ${percent}%;`
            : `${this.isRtl ? "right" : "left"}: ${percent}%;`;
    }

    getThumbId(index) {
        return `${this.state.id}-thumb-${index}`;
    }

    getThumbAriaLabel(index) {
        return this.props.ariaLabel || `Slider value ${index + 1}`;
    }

    getThumbAriaValueText(index, value) {
        if (typeof this.props.ariaValueText === "function") {
            return this.props.ariaValueText(value, index, this.currentValues);
        }
        if (Array.isArray(this.props.ariaValueText)) {
            return this.props.ariaValueText[index];
        }
        return this.props.ariaValueText;
    }

    valueToPercent(value) {
        const min = this.minimumValue;
        const max = this.maximumValue;
        if (max === min) {
            return 0;
        }
        return ((value - min) / (max - min)) * 100;
    }

    percentToValue(percent) {
        const min = this.minimumValue;
        const max = this.maximumValue;
        const rawValue = min + (clamp(percent, 0, 100) / 100) * (max - min);
        return clamp(roundToStep(rawValue, this.props.step, min), min, max);
    }

    getClosestThumbIndex(value) {
        let index = 0;
        let distance = Infinity;
        this.currentValues.forEach((item, itemIndex) => {
            const nextDistance = Math.abs(item - value);
            if (nextDistance < distance) {
                distance = nextDistance;
                index = itemIndex;
            }
        });
        return index;
    }

    updateValues(values, commit = false) {
        const payload = values.length === 1 ? values[0] : values;
        if (this.props.value === undefined) {
            this.state.values = values;
            if (status(this) === "mounted") {
                this.render(true);
            } else {
                this.pendingRender = true;
            }
        }
        this.props.onValueChange?.(payload, values);
        if (commit) {
            this.props.onValueCommit?.(payload, values);
        }
    }

    resolvePointerValue(ev) {
        const rect = this.trackRef.el?.getBoundingClientRect();
        if (!rect) {
            return this.currentValues[0];
        }
        const percent =
            this.props.orientation === "vertical"
                ? 100 - ((ev.clientY - rect.top) / rect.height) * 100
                : this.isRtl
                  ? 100 - ((ev.clientX - rect.left) / rect.width) * 100
                  : ((ev.clientX - rect.left) / rect.width) * 100;
        return this.percentToValue(percent);
    }

    updatePointerValue(ev) {
        const value = this.resolvePointerValue(ev);
        const values = [...this.currentValues];
        const index =
            this.state.activeThumbIndex ?? this.getClosestThumbIndex(value);
        const minDistance = this.minimumDistance;
        const minBound = index > 0 ? values[index - 1] + minDistance : this.minimumValue;
        const maxBound =
            index < values.length - 1 ? values[index + 1] - minDistance : this.maximumValue;
        values[index] = clamp(value, minBound, maxBound);
        this.updateValues(values);
    }

    startDrag(index, ev) {
        if (this.props.disabled) {
            ev.preventDefault();
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.state.activeThumbIndex = index;
        this.state.dragging = true;
    }

    onTrackPointerDown(ev) {
        if (this.props.disabled) {
            ev.preventDefault();
            return;
        }
        ev.preventDefault();
        const value = this.resolvePointerValue(ev);
        this.state.activeThumbIndex = this.getClosestThumbIndex(value);
        this.state.dragging = true;
        this.updatePointerValue(ev);
    }

    onPointerMove(ev) {
        if (!this.state.dragging) {
            return;
        }
        ev.preventDefault();
        this.updatePointerValue(ev);
    }

    endDrag() {
        if (!this.state.dragging) {
            return;
        }
        this.state.dragging = false;
        this.state.activeThumbIndex = null;
        const values = this.currentValues;
        const payload = values.length === 1 ? values[0] : values;
        this.props.onValueCommit?.(payload, values);
    }

    onThumbKeydown(index, ev) {
        const horizontal = this.props.orientation !== "vertical";
        const verticalDirection = { ArrowUp: 1, ArrowDown: -1 };
        const horizontalDirection = this.isRtl
            ? { ArrowRight: -1, ArrowLeft: 1 }
            : { ArrowRight: 1, ArrowLeft: -1 };
        const directionMap = horizontal ? horizontalDirection : verticalDirection;

        if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "End", "PageUp", "PageDown"].includes(ev.key)) {
            return;
        }
        ev.preventDefault();
        const values = [...this.currentValues];
        const minDistance = this.minimumDistance;
        const minBound = index > 0 ? values[index - 1] + minDistance : this.minimumValue;
        const maxBound = index < values.length - 1 ? values[index + 1] - minDistance : this.maximumValue;

        if (ev.key === "Home") {
            values[index] = minBound;
        } else if (ev.key === "End") {
            values[index] = maxBound;
        } else {
            const multiplier = ev.key === "PageUp" || ev.key === "PageDown" ? 10 : 1;
            const direction =
                ev.key === "PageUp" ? 1 : ev.key === "PageDown" ? -1 : directionMap[ev.key] || 0;
            values[index] = clamp(
                roundToStep(values[index] + direction * this.props.step * multiplier, this.props.step, this.minimumValue),
                minBound,
                maxBound
            );
        }
        this.updateValues(values, true);
    }
}
