import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import {
    Component,
    onWillRender,
    useEffect,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
export class ButtonBox extends Component {
    static template = "web.Form.ButtonBox";
    static components = { Dropdown, DropdownItem };
    static props = {
        slots: Object,
        class: { type: String, optional: true },
    };
    static defaultProps = {
        class: "",
    };

    setup() {
        const ui = useService("ui");
        this.rootRef = useRef("root");
        // max number of buttons that fit in the available width, null if not measured
        this.state = useState({ fittingButtons: null });
        let windowWidth = browser.innerWidth;
        const onWindowResize = useThrottleForAnimation(() => {
            const isWider = browser.innerWidth > windowWidth;
            windowWidth = browser.innerWidth;
            if (isWider && this.state.fittingButtons !== null) {
                // render all buttons again, the effect measures which ones fit
                this.state.fittingButtons = null;
            } else {
                this.computeFittingButtons();
            }
        });
        useExternalListener(window, "resize", onWindowResize);
        useEffect(() => this.computeFittingButtons());
        onWillRender(() => {
            let maxVisibleButtons = [0, 0, 7, 4, 5, 8][ui.size] ?? 8;
            if (this.state.fittingButtons !== null) {
                maxVisibleButtons = Math.min(maxVisibleButtons, this.state.fittingButtons);
            }
            const allVisibleButtons = Object.entries(this.props.slots)
                .filter(([_, slot]) => this.isSlotVisible(slot))
                .map(([slotName]) => slotName);
            if (allVisibleButtons.length <= maxVisibleButtons) {
                this.visibleButtons = allVisibleButtons;
                this.additionalButtons = [];
                this.isFull = allVisibleButtons.length === maxVisibleButtons;
            } else {
                // -1 for "More" dropdown
                const splitIndex = Math.max(maxVisibleButtons - 1, 0);
                this.visibleButtons = allVisibleButtons.slice(0, splitIndex);
                this.additionalButtons = allVisibleButtons.slice(splitIndex);
                this.isFull = true;
            }
        });
    }

    computeFittingButtons() {
        const el = this.rootRef.el;
        if (!el?.children.length || this.env.isSmall) {
            return;
        }
        // Buttons don't shrink, so move the ones that overflow to the "More" dropdown
        const boxRect = el.getBoundingClientRect();
        const isRTL = getComputedStyle(el).direction === "rtl";
        const getEnd = (button) => {
            const rect = button.getBoundingClientRect();
            return isRTL ? boxRect.right - rect.left : rect.right - boxRect.left;
        };
        const buttons = [...el.children];
        if (getEnd(buttons.at(-1)) <= boxRect.width + 1) {
            return;
        }
        const moreButtonWidth = this.additionalButtons.length
            ? buttons.pop().getBoundingClientRect().width
            : parseFloat(getComputedStyle(buttons[0]).minWidth) || 0;
        const fittingButtons = buttons.filter(
            (button) => getEnd(button) + moreButtonWidth <= boxRect.width + 1
        ).length;
        // +1 for "More" dropdown, and at least one button less than now so it ends
        this.state.fittingButtons = Math.min(fittingButtons + 1, el.children.length - 1);
    }

    isSlotVisible(slot) {
        return !("isVisible" in slot) || slot.isVisible;
    }
}
