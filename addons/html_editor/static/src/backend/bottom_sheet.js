import { patch } from "@web/core/utils/patch";
import { BottomSheet } from "@web/core/bottom_sheet/bottom_sheet";
import { onMounted, onWillUnmount, t, useListener, useProps } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useViewportChange } from "@web/core/utils/dvu";
import { useThrottleForAnimation } from "@web/core/utils/timing";

/**
 * @param {Element|null} el the active element of a document
 * @returns {boolean} whether the focus is in an editable, possibly within an
 *     iframe (e.g. an editor displayed in an iframe)
 */
function isEditableFocused(el) {
    if (el?.tagName === "IFRAME") {
        try {
            return isEditableFocused(el.contentDocument?.activeElement);
        } catch {
            return false; // Cross-origin iframe
        }
    }
    return !!el?.isContentEditable;
}

patch(BottomSheet.prototype, {
    setup() {
        super.setup();
        this.htmlEditorProps = useProps({
            withUnfocus: t.boolean().optional(false),
            fitOnResize: t.boolean().optional(false),
        });
        onMounted(() => {
            const activeElement = this.sheetRef().ownerDocument.activeElement;
            // Only unfocus an editable, to hide the text selection widgets of
            // the OS: other elements (e.g. an input in the sheet content) keep
            // their focus.
            if (this.htmlEditorProps.withUnfocus && isEditableFocused(activeElement)) {
                this.elementToRefocus = activeElement;
                this.elementToRefocus.blur();
            }
        });
        onWillUnmount(() => {
            const elementToRefocus = this.elementToRefocus;
            const containerEl = this.containerRef();
            const doc = containerEl.ownerDocument;
            const activeElement = doc.activeElement;
            // Give the focus back to the element that had it before opening,
            // e.g. the editable, unless the user focused something else since.
            if (
                !elementToRefocus ||
                elementToRefocus === doc.body ||
                (activeElement &&
                    activeElement !== doc.body &&
                    !containerEl.contains(activeElement))
            ) {
                return;
            }
            // Wait for the sheet to leave the DOM: the element might not be
            // focusable while a bottom sheet is displayed (e.g. the toolbar),
            // and only if nothing else took the focus meanwhile (e.g. a dialog
            // opened from the sheet).
            Promise.resolve().then(() => {
                const active = doc.activeElement;
                if (
                    elementToRefocus.isConnected &&
                    (!active || active === doc.body || !active.isConnected)
                ) {
                    elementToRefocus.focus({ preventScroll: true });
                }
            });
        });
        if (this.htmlEditorProps.fitOnResize) {
            // Runs after the default viewport change handler, which updates
            // the dimensions but disables snapping without restoring it: the
            // sheet would stay wherever the keyboard toggle left it.
            useViewportChange(() => {
                if (this.state.isPositionedReady && !this.state.isDismissing) {
                    this.fitToVisualViewport();
                    this.positionSheet();
                    this.updateProgressValue(this.scrollRailRef().scrollTop);
                    this.state.isSnappingEnabled = true;
                }
            });
            // The keyboard might already be displayed when opening the sheet.
            onMounted(() => this.fitToVisualViewport());
            // The browser may pan the visual viewport (e.g. to reveal the
            // focused input) without resizing it.
            if (browser.visualViewport) {
                const throttledFit = useThrottleForAnimation(() => this.fitToVisualViewport());
                useListener(browser.visualViewport, "scroll", throttledFit);
            }
        }
    },

    /**
     * Keeps the bottom of the sheet at the bottom of the visual viewport.
     * On some mobile browsers (e.g. Chrome Android), the virtual keyboard
     * only shrinks the visual viewport: the layout viewport, to which the
     * sheet is anchored, keeps its height, so the sheet would end up behind
     * the keyboard, more or less depending on how the browser panned the
     * visual viewport to reveal the focused element.
     */
    fitToVisualViewport() {
        const containerEl = this.containerRef();
        const visualViewport = browser.visualViewport;
        if (!containerEl || !visualViewport) {
            return;
        }
        const hiddenBelow =
            containerEl.clientHeight - (visualViewport.offsetTop + visualViewport.height);
        // Moving the container up keeps its dvh height: the sheet dimensions,
        // expressed in dvh, remain valid.
        // Ignore subpixel differences due to fractional viewport heights.
        containerEl.style.top = hiddenBelow >= 1 ? `${-hiddenBelow}px` : "";
    },

    onIframeLoad(ev) {
        const doc = this.sheetRef().ownerDocument;
        if (doc.hasFocus() && !doc.getSelection().isCollapsed) {
            // Hide mobile text selection widgets by focusing something else
            // without losing in-document selection.
            const iframeDoc = ev.target.contentDocument;
            if (!iframeDoc.hasFocus()) {
                const defaultActiveElement = doc.activeElement;
                const inputEl = iframeDoc.querySelector("input");
                inputEl.focus();
                // Somehow this does not display the keyboard - which is what we want.
                // If we disable the field, some phones keep displaying the selection widgets.
                if (defaultActiveElement) {
                    // But we need to restore the actual default focused element.
                    defaultActiveElement.focus();
                    inputEl.remove();
                }
            }
        }
    },
});
