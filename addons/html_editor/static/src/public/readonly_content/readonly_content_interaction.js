import { fillClipboardWithSelection } from "@html_editor/utils/clipboard";
import { getImageFileModel } from "@html_editor/utils/image";
import { wrapReadonlyTables } from "@html_editor/utils/table";
import { getLinksToRetarget, retargetLinkToNewTab } from "@html_editor/utils/url";
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
            "t-on-copy.noUpdate": fillClipboardWithSelection,
            "t-on-dblclick.noUpdate": this.onImageDoubleClick,
        },
        "[data-oe-role]": {
            "t-att-role": (el) => el.dataset.oeRole,
        },
        "[data-oe-aria-label]": {
            "t-att-aria-label": (el) => el.dataset.oeAriaLabel,
        },
    };

    setup() {
        this.fileViewer = this.services.fileViewer();
        this.registerCleanup(() => this.fileViewer.close());
    }

    onImageDoubleClick({ target }) {
        const embedded = target.closest("[data-embedded], [data-embedded-editable]");
        if (target.tagName === "IMG" && !embedded?.matches("[data-embedded]")) {
            this.fileViewer.open(getImageFileModel(target));
        }
    }

    start() {
        for (const link of getLinksToRetarget(this.el)) {
            retargetLinkToNewTab(link);
        }
        wrapReadonlyTables(this.el);
    }
}

registry
    .category("public.interactions")
    .add("html_editor.readonly_content", ReadonlyContentInteraction);
