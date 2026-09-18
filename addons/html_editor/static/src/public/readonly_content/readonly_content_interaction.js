import { fillHtmlTransferData } from "@html_editor/utils/clipboard";
import { unwrapContents } from "@html_editor/utils/dom";
import { wrapTables } from "@html_editor/utils/table";
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

    setup() {
        this.tableWrappers = [];
    }

    start() {
        this.tableWrappers = wrapTables(this.el);
    }

    destroy() {
        // Leave the content as it was found, interactions can be started on it
        // again. A container without parent went away with the content that was
        // replaced in the meantime, e.g. by an html migration.
        for (const wrapper of this.tableWrappers) {
            if (wrapper.parentNode) {
                unwrapContents(wrapper);
            }
        }
    }

    /**
     * Copy the selection with its html, so that it keeps its formatting once
     * pasted in an editor.
     *
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
