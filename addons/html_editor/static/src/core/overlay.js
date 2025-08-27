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
import { closestScrollableY } from "@web/core/utils/scrolling";

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
        history: Object,
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
        const container = closestScrollable(editable) || topDocument.documentElement;
        const resizeObserver = new ResizeObserver(() => position.unlock());
        resizeObserver.observe(container);
        onWillDestroy(() => resizeObserver.disconnect());
        const positionOptions = {
            position: "bottom-start",
            container: container,
            ...this.props.positionOptions,
            onPositioned: (el, solution) => {
                this.props.positionOptions?.onPositioned?.(el, solution);
                this.updateVisibility(el, solution, container);
            },
        };
        position = usePosition("root", getTarget, positionOptions);

        this.overlayState = useState({ isOverlayVisible: true });
        useSubEnv({ overlayState: this.overlayState });
    }

    getSelectionTarget() {
        const doc = this.props.editable.ownerDocument;
        const selection = doc.getSelection();
        if (!selection || !selection.rangeCount || !this.props.isOverlayOpen()) {
            return null;
        }
        const inEditable = this.props.editable.contains(selection.anchorNode);
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
            this.props.history.ignoreDOMMutations(() => {
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

    updateVisibility(overlayElement, solution, container) {
        // @todo: mobile tests rely on a visible (yet overflowing) toolbar
        // Remove this once the mobile toolbar is fixed?
        if (this.env.isSmall) {
            return;
        }
        const shouldBeVisible = this.shouldOverlayBeVisible(overlayElement, solution, container);
        overlayElement.style.visibility = shouldBeVisible ? "visible" : "hidden";
        this.overlayState.isOverlayVisible = shouldBeVisible;
    }

    /**
     * @param {HTMLElement} overlayElement
     * @param {Object} solution
     * @param {HTMLElement} container
     */
    shouldOverlayBeVisible(overlayElement, solution, container) {
        const containerRect = container.getBoundingClientRect();
        const overflowsTop = solution.top < containerRect.top;
        const overflowsBottom = solution.top + overlayElement.offsetHeight > containerRect.bottom;
        const canFlip = this.props.positionOptions?.flip ?? true;
        if (overflowsTop) {
            if (overflowsBottom) {
                // Overlay is bigger than the cointainer. Hiding it would it
                // make always invisible.
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
 * Wrapper around closestScrollableY that keeps searching outside of iframes.
 *
 * @param {HTMLElement} el
 */
function closestScrollable(el) {
    if (!el) {
        return null;
    }
    return closestScrollableY(el) || closestScrollable(el.ownerDocument.defaultView.frameElement);
}
