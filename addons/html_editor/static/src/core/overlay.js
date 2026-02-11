import {
    Component,
    onWillDestroy,
    useEffect,
    useExternalListener,
    useRef,
    useState,
    useSubEnv,
    xml,
} from "@odoo/owl";
import { OVERLAY_SYMBOL } from "@web/core/overlay/overlay_container";
import { usePosition } from "@web/core/position/position_hook";
import { useActiveElement } from "@web/core/ui/ui_service";

export class EditorOverlay extends Component {
    static template = xml`
        <div t-ref="root" class="overlay" t-att-class="props.className" t-on-pointerdown.stop="() => {}">
            <t t-component="props.Component" t-props="props.props"/>
        </div>`;

    static props = {
        target: { validate: (el) => el.nodeType === Node.ELEMENT_NODE, optional: true },
        initialSelection: { type: Object, optional: true },
        Component: Function,
        props: { type: Object, optional: true },
        editable: { validate: (el) => el.nodeType === Node.ELEMENT_NODE },
        bus: Object,
        shared: Object,
        close: Function,
        isOverlayOpen: Function,

        // Props from createOverlay
        positionOptions: { type: Object, optional: true },
        className: { type: String, optional: true },
        closeOnPointerdown: { type: Boolean, optional: true },
        hasAutofocus: { type: Boolean, optional: true },
    };

    static defaultProps = {
        className: "",
        closeOnPointerdown: true,
        hasAutofocus: false,
    };

    setup() {
        this.lastSelection = this.props.initialSelection;
        /** @type {HTMLElement} */
        const editable = this.props.editable;
        let getTarget, position;
        if (this.props.target) {
            getTarget = () => this.props.target;
        } else {
            this.rangeElement = editable.ownerDocument.createElement("range-el");
            editable.after(this.rangeElement);
            onWillDestroy(() => {
                this.rangeElement.remove();
            });
            getTarget = this.getSelectionTarget.bind(this);
        }

        useExternalListener(this.props.bus, "updatePosition", () => {
            position.unlock();
        });

        const rootRef = useRef("root");

        if (this.props.positionOptions?.updatePositionOnResize ?? true) {
            const resizeObserver = new ResizeObserver(() => {
                position.unlock();
            });
            useEffect(
                (root) => {
                    resizeObserver.observe(root);
                    return () => {
                        resizeObserver.unobserve(root);
                    };
                },
                () => [rootRef.el]
            );
        }

        if (this.props.closeOnPointerdown) {
            const clickAway = (ev) => {
                if (!this.env[OVERLAY_SYMBOL]?.contains(ev.composedPath()[0])) {
                    this.props.close();
                }
            };
            const editableDocument = this.props.editable.ownerDocument;
            useExternalListener(editableDocument, "pointerdown", clickAway);
            // Listen to pointerdown outside the iframe
            if (editableDocument !== document) {
                useExternalListener(document, "pointerdown", clickAway);
            }
        }

        if (this.props.hasAutofocus) {
            useActiveElement("root");
        }
        const topDocument = editable.ownerDocument.defaultView.top.document;
        const scrollContainer = getScrollContainer(editable);
        const container = scrollContainer || topDocument.documentElement;
        const resizeObserver = new ResizeObserver(() => position.unlock());
        resizeObserver.observe(container);
        onWillDestroy(() => resizeObserver.disconnect());
        const positionOptions = {
            position: "bottom-start",
            container: container,
            ...this.props.positionOptions,
            onPositioned: (el, solution) => {
                this.props.positionOptions?.onPositioned?.(el, solution);
                this.updateVisibility(el, solution, scrollContainer);
            },
        };
        position = usePosition("root", getTarget, positionOptions);

        this.overlayState = useState({ isOverlayVisible: true });
        useSubEnv({ overlayState: this.overlayState });
    }

    getSelectionTarget() {
        const doc = this.props.editable.ownerDocument;
        const selection = doc.getSelection();
        const selectionData = this.props.shared.getSelectionData();
        if (!selection || !selection.rangeCount || !this.props.isOverlayOpen()) {
            return null;
        }
        const inEditable = selectionData.currentSelectionIsInEditable;
        let range;
        if (inEditable) {
            range = selection.getRangeAt(0);
            this.lastSelection = { range };
        } else {
            if (!this.lastSelection) {
                return null;
            }
            range = this.lastSelection.range;
        }
        let rect = range.getBoundingClientRect();
        if (rect.x === 0 && rect.width === 0 && rect.height === 0) {
            // Attention, ignoring DOM mutations is always dangerous (when we add or remove nodes)
            // because if another mutation uses the target that is not observed, that mutation can never be applied
            // again (when undo/redo and in collaboration).
            this.props.shared.ignoreDOMMutations(() => {
                const clonedRange = range.cloneRange();
                const shadowCaret = doc.createTextNode("|");
                clonedRange.insertNode(shadowCaret);
                clonedRange.selectNode(shadowCaret);
                rect = clonedRange.getBoundingClientRect();
                shadowCaret.remove();
                clonedRange.detach();
            });
        }
        // Html element with a patched getBoundingClientRect method. It
        // represents the range as a (HTMLElement) target for the usePosition
        // hook.
        this.rangeElement.getBoundingClientRect = () => rect;
        return this.rangeElement;
    }

    updateVisibility(overlayElement, solution, scrollContainer) {
        // @todo: mobile tests rely on a visible (yet overflowing) toolbar
        // Remove this once the mobile toolbar is fixed?
        if (this.env.isSmall) {
            return;
        }
        const shouldBeVisible = this.shouldOverlayBeVisible(
            overlayElement,
            solution,
            scrollContainer
        );
        overlayElement.style.visibility = shouldBeVisible ? "visible" : "hidden";
        this.overlayState.isOverlayVisible = shouldBeVisible;
    }

    /**
     * @param {HTMLElement} overlayElement
     * @param {Object} solution
     * @param {HTMLElement} scrollContainer
     */
    shouldOverlayBeVisible(overlayElement, solution, scrollContainer) {
        if (!scrollContainer) {
            return true;
        }
        const scrollContainerRect = scrollContainer.getBoundingClientRect();
        let scrollContainerTop = scrollContainerRect.top;
        if (scrollContainer.ownerDocument !== overlayElement.ownerDocument) {
            const frameElement = scrollContainer.ownerDocument.defaultView?.frameElement;
            if (frameElement) {
                scrollContainerTop += frameElement.getBoundingClientRect().top;
            }
        }
        const top = Math.max(scrollContainerTop, 0);
        const bottom = top + scrollContainerRect.height;
        const overflowsTop = solution.top < top;
        const overflowsBottom = solution.top + overlayElement.offsetHeight > bottom;
        const canFlip = this.props.positionOptions?.flip ?? true;
        if (overflowsTop) {
            if (overflowsBottom) {
                // Overlay is bigger than the cointainer. Hiding it would make
                // it always invisible.
                return true;
            }
            if (solution.direction === "top" && canFlip) {
                // Scrolling down will make overlay eventually flip and no longer overflow
                return true;
            }
            return false;
        }
        if (overflowsBottom) {
            if (solution.direction === "bottom" && canFlip) {
                // Scrolling up will make overlay eventually flip and no longer overflow
                return true;
            }
            return false;
        }
        return true;
    }
}

/**
 * The scroll container is an ancestor of {@link el} that is:
 * - scrollable and
 * - not also ancestor of a fixed element encosing `el` in the same
 * document (as this makes `el` fixed and not affected by scrolls of
 * that ancestor)
 *
 * @param {HTMLElement} el
 * @returns {HTMLElement|null}
 */
export function getScrollContainer(el) {
    const isScrollable = (/** @type {HTMLElement} */ el) => {
        if (el.tagName === "HTML") {
            return el.scrollHeight > el.ownerDocument.defaultView.visualViewport.height;
        }
        return (
            el.scrollHeight > el.clientHeight &&
            /\bauto\b|\bscroll\b/.test(getComputedStyle(el)["overflow-y"])
        );
    };
    const isFixed = (el) => getComputedStyle(el).position === "fixed";
    while (el) {
        if (isScrollable(el)) {
            return el;
        }
        if (isFixed(el)) {
            // Any scrollable ancestor in the same document does not affect it.
            // Search in the enclosing document, if any.
            el = el.ownerDocument.defaultView.frameElement;
            continue;
        }
        el = el.parentElement || el.ownerDocument.defaultView.frameElement;
    }
    return null;
}
