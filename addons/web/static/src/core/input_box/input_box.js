import { useForwardRefToParent } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { hasTouch } from "@web/core/browser/feature_detection";
import { browser } from "@web/core/browser/browser";
import { Component } from "@odoo/owl";
import { getVisibleElements } from "../utils/ui";

function _positionInputBoxOverlay(target) {
    const _hasTouch = hasTouch();
    const closestInputBox =
        target.closest(".o_input_box:not(.o_input_box .o_input_box)") ||
        target.querySelector(".o_input_box");
    if (!closestInputBox) {
        return;
    }
    const startOverlays = getVisibleElements(closestInputBox, `.o_input_box_overlay_start`);
    const endOverlays = getVisibleElements(closestInputBox, `.o_input_box_overlay_end`);
    if (!startOverlays.length && !endOverlays.length) {
        return;
    }
    let startPadding = 0;
    let endPadding = 0;
    const gap = parseInt(
        getComputedStyle(closestInputBox).getPropertyValue("--inputbox-spacing-unit")
    );
    for (let i = 0; i < startOverlays.length; i++) {
        const offset = startPadding > 0 ? ` + ${startPadding}px` : "";
        startOverlays[i].style["inset-inline-start"] = `calc((1.5 * var(--inputbox-overlay-padding-x)) ${offset})`;
        startPadding += startOverlays[i].clientWidth + gap;
    };
    closestInputBox.style.setProperty("--inputbox-overlay-start-size", startPadding + "px");
    for (let i = endOverlays.length; i > 0; i--) {
        const overlay = endOverlays[i - 1];
        if (_hasTouch && overlay.classList.contains("btn-link")) {
            overlay.classList.add("btn-secondary");
            overlay.classList.remove("btn-link");
        }
        const offset = endPadding > 0 ? ` + ${endPadding}px` : "";
        overlay.style["inset-inline-end"] = `calc(var(--inputbox-overlay-padding-x) ${offset})`;
        endPadding += overlay.clientWidth + gap;
    }
    closestInputBox.style.setProperty("--inputbox-overlay-end-size", endPadding + "px");
    const inlineEl = closestInputBox.querySelector(".o_input_box_overlay_inline");
    if (inlineEl) {
        const inputEl = closestInputBox.querySelector(
            ".o_input, textarea, select, [contenteditable]"
        );
        if (inputEl && inputEl.value) {
            const length = inputEl.value.length;
            closestInputBox.style.setProperty(
                "--inputbox-overlay-inline-position",
                `calc(100% - (${length}px + ${
                    length * 0.5
                }rem) - var(--inputbox-overlay-size) - var(--inputbox-spacing-unit))`
            );
        }
    }
}

export function positionInputBoxOverlay(target) {
    if (target) {
        requestAnimationFrame(() => _positionInputBoxOverlay(target));
    }
}

export class InputBox extends Component {
    static template = "web.InputBox";
    static components = { Dropdown, DropdownItem };
    static defaultProps = {
        type: "text",
    };
    static props = {
        id: { type: String, optional: true },
        input: { type: Function, optional: true },
        overlayButtons: { type: Array, optional: true },
        placeholder: { type: String, optional: true },
        required: { type: Boolean, optional: true },
        type: { type: String, optional: true },
    };

    setup() {
        this.inputRef = useForwardRefToParent("input");
        this.hasTouch = hasTouch();
    }

    get overlayButtons() {
        if (this.props.overlayButtons) {
            return this.props.overlayButtons.map((btn) => ({
                ...btn,
                onSelected: btn.onSelected || (() => browser.open(btn.href))
            }));
        }
        return [];
    }

    get buttonClass() {
        return "o_input_box_overlay_end btn btn-link";
    }
}
