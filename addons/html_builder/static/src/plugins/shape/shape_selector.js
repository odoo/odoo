import { proxy, signal, useProps, t } from "@odoo/owl";
import { ImgGroup } from "@html_builder/core/img_group";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { getShapeURL } from "../image/image_helpers";
import { useAutofocus } from "@web/core/utils/hooks";

export const shapeSelectorProps = {
    onClose: t.function(),
    selectorTitle: t.string(),
    shapeGroups: t.object(),
    shapeActionId: t.string(),
    buttonWrapperClassName: t.string().optional(),
    imgThroughDiv: t.boolean().optional(),
    getShapeUrl: t.function().optional(),
    getShapeStyle: t.function().optional(),
};

export class ShapeSelector extends BaseOptionComponent {
    static template = "html_builder.shapeSelector";
    props = useProps(shapeSelectorProps);
    static components = { ImgGroup };
    rootRef = signal.ref();
    tabsRef = signal.ref();
    backButtonRef = signal.ref();

    setup() {
        super.setup();
        this.state = proxy({ activeGroup: "basic" });
        this.onScroll = useThrottleForAnimation(this._onScroll.bind(this));
        useAutofocus({ ref: this.backButtonRef });
    }
    getShapeUrl(shapePath) {
        return this.props.getShapeUrl ? this.props.getShapeUrl(shapePath) : getShapeURL(shapePath);
    }
    getShapeClass(shapePath) {
        return `o_${shapePath.replaceAll("/", "_")}`;
    }
    scrollToShapes(id) {
        const container = this.rootRef();
        const selectedElement = container?.querySelector(`[data-shape-group-id="${id}"]`);
        if (container && selectedElement) {
            container.scrollTop = selectedElement.offsetTop - container.offsetTop;
        }
    }

    _onScroll() {
        const pagerContainerRect = this.rootRef().getBoundingClientRect();
        // The threshold for when a menu element is defined as 'active' is half
        // of the container's height. This has a drawback as if a section
        // is too small it might never get `active` if it's the last section.
        const threshold = pagerContainerRect.height / 2;

        const anchorEls = this.tabsRef().querySelectorAll(".o-hb-select-pager-tab");
        for (const anchorEl of anchorEls) {
            const groupId = anchorEl.dataset.groupId;
            const sectionEl = this.rootRef().querySelector(`[data-shape-group-id="${groupId}"]`);
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
