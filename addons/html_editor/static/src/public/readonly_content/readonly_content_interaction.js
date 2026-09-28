import { fillHtmlTransferData } from "@html_editor/utils/clipboard";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

/**
 * Process readonly content that is rendered by the server rather than by the
 * `HtmlViewer`, e.g. a Knowledge article shared with public users, the way the
 * viewer does in `processReadonlyContent`.
 */
export class ReadonlyContentInteraction extends Interaction {
    static selector = ".o_readonly";

    dynamicContent = {
        _root: {
            "t-on-copy.noUpdate": this.onCopy,
        },
        "[data-oe-role]": {
            "t-att-role": (el) => el.dataset.oeRole,
        },
        "[data-oe-aria-label]": {
            "t-att-aria-label": (el) => el.dataset.oeAriaLabel,
        },
        // External links open in a new tab.
        [`a:not([href^="${browser.location.origin}"]):not([href^="/"])`]: {
            "t-att-target": () => "_blank",
            "t-att-rel": () => "noreferrer",
        },
    };

    /**
     * @param {ClipboardEvent} ev
     */
    onCopy(ev) {
        ev.preventDefault();
        const selection = this.el.ownerDocument.getSelection();
        fillHtmlTransferData(ev, "clipboardData", selection.getRangeAt(0).cloneContents(), {
            textContent: selection.toString(),
        });
    }
}

registry
    .category("public.interactions")
    .add("html_editor.readonly_content", ReadonlyContentInteraction);
