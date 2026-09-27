import { ancestors } from "@html_editor/utils/dom_traversal";
import { Plugin } from "../plugin";
import { debounce, throttleForAnimation } from "@web/core/utils/timing";
import { couldBeScrollableX, couldBeScrollableY } from "@web/core/utils/scrolling";
import { NATIVE_MUTATION_TYPES } from "@html_editor/core/dom_observer_plugin";

/**
 * @typedef {(() => void)[]} on_layout_geometry_change_handlers
 */
/**
 * This plugin broadcasts layout/geometry changes to other plugins when
 * scrolling, resizing, or history changes occur.
 */
export class PositionPlugin extends Plugin {
    static id = "position";
    static dependencies = ["domObserver"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        on_history_rebased_handlers: this.layoutGeometryChange.bind(this),
        on_committed_to_history_handlers: this.layoutGeometryChange.bind(this),
        on_will_filter_mutations_handlers: this.handlePotentialLayoutGeometryChange.bind(this),
    };

    setup() {
        this.layoutGeometryChange = throttleForAnimation(this.layoutGeometryChange.bind(this));
        this.debouncedLayoutGeometryChange = debounce(
            this.layoutGeometryChange.bind(this),
            "animationFrame"
        );
        this.resizeObserver = new ResizeObserver(this.layoutGeometryChange);
        this.resizeObserver.observe(this.document.body);
        this.resizeObserver.observe(this.editable);
        this.addDomListener(window, "resize", this.layoutGeometryChange);
        if (this.window !== window) {
            this.addDomListener(this.window, "resize", this.layoutGeometryChange);
        }
        const scrollableElements = [
            this.editable,
            ...ancestors(this.editable).filter(
                (node) => couldBeScrollableX(node) || couldBeScrollableY(node)
            ),
        ];
        for (const scrollableElement of scrollableElements) {
            this.addDomListener(scrollableElement, "scroll", () => {
                this.layoutGeometryChange();
            });
            this.resizeObserver.observe(scrollableElement);
        }
    }

    /**
     * @param {import("@html_editor/core/dom_observer_plugin").NativeMutation[]} mutations
     */
    handlePotentialLayoutGeometryChange(mutations) {
        const hasClassChange = (mutation) => {
            const { addedClasses, removedClasses } =
                this.dependencies.domObserver.getClassChanges(mutation);
            return !!new Set([...addedClasses, ...removedClasses]).size;
        };
        if (
            mutations.find((mutation) => {
                const attribute =
                    mutation.type === NATIVE_MUTATION_TYPES.ATTRIBUTES && mutation.attributeName;
                return attribute === "style" || (attribute === "class" && hasClassChange(mutation));
            })
        ) {
            this.debouncedLayoutGeometryChange();
            return;
        }
    }
    destroy() {
        this.resizeObserver.disconnect();
        super.destroy();
    }
    layoutGeometryChange() {
        this.trigger("on_layout_geometry_change_handlers");
    }
}
