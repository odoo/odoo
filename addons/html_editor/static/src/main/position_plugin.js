import { ancestors } from "@html_editor/utils/dom_traversal";
import { Plugin } from "../plugin";
import { throttleForAnimation } from "@web/core/utils/timing";
import { couldBeScrollableX, couldBeScrollableY } from "@web/core/utils/scrolling";

/**
 * This plugins provides a way to create a "local" overlays so that their
 * visibility is relative to the overflow of their ancestors.
 */
export class PositionPlugin extends Plugin {
    static name = "position";
    resources = {
        // todo: it is strange that the position plugin is aware of onExternalHistorySteps and historyResetFromSteps.
        onExternalHistorySteps: this.layoutGeometryChange.bind(this),
        historyResetFromSteps: this.layoutGeometryChange.bind(this),
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

    handleCommand(commandName) {
        switch (commandName) {
            case "ADD_STEP":
                this.layoutGeometryChange();
                break;
        }
    }
    destroy() {
        this.resizeObserver.disconnect();
        super.destroy();
    }
    layoutGeometryChange() {
        this.getResource("layoutGeometryChange").forEach((cb) => cb());
    }
}
