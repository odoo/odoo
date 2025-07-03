import { useRef, useState } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { getShapeURL } from "../image/image_helpers";

export class ShapeSelector extends BaseOptionComponent {
    static template = "html_builder.shapeSelector";
    static props = {
        onClose: Function,
        selectorTitle: String,
        shapeGroups: Object,
        shapeActionId: String,
        buttonWrapperClassName: { type: String, optional: true },
        imgThroughDiv: { type: Boolean, optional: true },
        getShapeUrl: { type: Function, optional: true },
    };

    setup() {
        super.setup();
        this.rootRef = useRef("root");
        this.tabsRef = useRef("tabs");
        this.state = useState({ activeGroup: "basic" });
        this.onScroll = useThrottleForAnimation(this._onScroll);
    }
    getShapeUrl(shapePath) {
        return this.props.getShapeUrl ? this.props.getShapeUrl(shapePath) : getShapeURL(shapePath);
    }
    getShapeClass(shapePath) {
        return `o_${shapePath.replaceAll("/", "_")}`;
    }
    scrollToShapes(id) {
        this.rootRef.el
            ?.querySelector(`[data-shape-group-id="${id}"]`)
            ?.scrollIntoView({ behavior: "smooth" });
    }

    _onScroll() {
        const pagerContainerRect = this.rootRef.el.getBoundingClientRect();
        // The threshold for when a menu element is defined as 'active' is half
        // of the container's height. This has a drawback as if a section
        // is too small it might never get `active` if it's the last section.
        const threshold = pagerContainerRect.height / 2;

        const anchorEls = this.tabsRef.el.querySelectorAll(".o-hb-select-pager-tab");
        for (const anchorEl of anchorEls) {
            const groupId = anchorEl.dataset.groupId;
            const sectionEl = this.rootRef.el.querySelector(`[data-shape-group-id="${groupId}"]`);
            const nextSectionEl = sectionEl.nextElementSibling;

            const sectionTop = sectionEl.getBoundingClientRect().top - pagerContainerRect.top;
            const nextSectionTop =
                nextSectionEl && nextSectionEl.getBoundingClientRect().top - pagerContainerRect.top;
            if (sectionTop < threshold && (!nextSectionEl || nextSectionTop > threshold)) {
                this.state.activeGroup = groupId;
            }
        }
    }
}
