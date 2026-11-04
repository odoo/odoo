import { ancestors } from "@html_editor/utils/dom_traversal";
import { Plugin } from "../plugin";
import { throttleForAnimation } from "@web/core/utils/timing";
import { couldBeScrollableX, couldBeScrollableY } from "@web/core/utils/scrolling";

/**
 * This plugin broadcasts layout/geometry changes to other plugins when
 * scrolling, resizing, or history changes occur.
 */
export class PositionPlugin extends Plugin {
    static id = "position";
    resources = {
        // todo: it is strange that the position plugin is aware of external_history_step_handlers and history_reset_from_steps_handlers.
        external_history_step_handlers: this.layoutGeometryChange.bind(this),
        history_reset_from_steps_handlers: this.layoutGeometryChange.bind(this),
        step_added_handlers: this.layoutGeometryChange.bind(this),
    };

    setup() {
        this.layoutGeometryChange = throttleForAnimation(this.layoutGeometryChange.bind(this));
        this.resizeObserver = new ResizeObserver(this.layoutGeometryChange);
        this.resizeObserver.observe(this.document.body);
        this.resizeObserver.observe(this.editable);
        this.addDomListener(window, "resize", this.layoutGeometryChange);
        if (this.document.defaultView !== window) {
            this.addDomListener(this.document.defaultView, "resize", this.layoutGeometryChange);
        }
        const scrollableElements = [this.editable, ...ancestors(this.editable)].filter((node) => {
            return couldBeScrollableX(node) || couldBeScrollableY(node);
        });
        for (const scrollableElement of scrollableElements) {
            this.addDomListener(scrollableElement, "scroll", () => {
                this.layoutGeometryChange();
            });
            this.resizeObserver.observe(scrollableElement);
        }
    }

    destroy() {
        this.resizeObserver.disconnect();
        super.destroy();
    }
    layoutGeometryChange() {
        this.dispatchTo("layout_geometry_change_handlers");
    }
}
