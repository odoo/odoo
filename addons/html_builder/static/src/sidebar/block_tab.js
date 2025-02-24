import { Component, useState } from "@odoo/owl";
import { useDraggable } from "@web/core/utils/draggable";
import { useService } from "@web/core/utils/hooks";
import { Tooltip } from "@web/core/tooltip/tooltip";
import { Snippet } from "./snippet";
import { CustomInnerSnippet } from "./custom_inner_snippet";
import { _t } from "@web/core/l10n/translation";

// TODO move it in web (copy from web_studio)
function copyElementOnDrag() {
    let element;
    let copy;

    function clone(_element) {
        element = _element;
        copy = element.cloneNode(true);
    }

    function insert() {
        if (element) {
            element.insertAdjacentElement("beforebegin", copy);
        }
    }

    function clean() {
        if (copy) {
            copy.remove();
        }
        copy = null;
        element = null;
    }

    return { clone, insert, clean };
}

export class BlockTab extends Component {
    static template = "html_builder.BlockTab";
    static components = { Snippet, CustomInnerSnippet };
    static props = {};

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.popover = useService("popover");
        this.snippetModel = useState(useService("html_builder.snippets"));

        this.dragState = {};
        const copyOnDrag = copyElementOnDrag();
        useDraggable({
            ref: this.env.builderRef,
            elements: ".o-website-builder_sidebar .o_draggable",
            enable: () => this.env.editor?.isReady,
            iframeWindow: this.env.editor?.editable.ownerDocument.defaultView,
            onWillStartDrag: ({ element }) => {
                this.hideSnippetToolTip?.();
                copyOnDrag.clone(element);
            },
            onDragStart: ({ element }) => {
                copyOnDrag.insert();
                const category = element.closest(".o_snippets_container").id;
                const id = element.dataset.id;
                const snippet = this.snippetModel.getSnippet(category, id);
                this.dragState = { category, id, snippet };
                this.dropzonePlugin.displayDropZone(snippet);
            },
            onDrag: ({ element }) => {
                this.dropzonePlugin.dragElement(element);
            },
            onDrop: ({ element }) => {
                const { x, y, height, width } = element.getClientRects()[0];
                const position = { x, y, height, width };
                const { category, snippet } = this.dragState;
                if (category === "snippet_groups") {
                    this.openSnippetDialog(snippet, position);
                    return;
                }
                const addElement = this.dropzonePlugin.getAddElement(position);
                if (!addElement) {
                    return;
                }
                addElement(snippet.content.cloneNode(true));
            },
            onDragEnd: () => {
                copyOnDrag.clean();
            },
        });
    }

    get dropzonePlugin() {
        return this.env.editor.shared.dropzone;
    }

    openSnippetDialog(snippet, position) {
        if (snippet.moduleId) {
            return;
        }
        if (!position) {
            this.dropzonePlugin.displayDropZone(snippet);
        }
        const addElement = this.dropzonePlugin.getAddElement(position);
        if (!addElement) {
            return;
        }
        this.snippetModel.select(snippet, {
            onSelect: (snippet) => {
                const newSnippet = snippet.content.cloneNode(true);
                addElement(newSnippet);
                return newSnippet;
            },
            onClose: () => this.dropzonePlugin.clearDropZone(),
        });
    }

    showSnippetTooltip(ev) {
        const snippetEl = ev.currentTarget.closest(".o_snippet.o_draggable");
        if (snippetEl) {
            this.hideSnippetToolTip?.();
            this.hideSnippetToolTip = this.popover.add(snippetEl, Tooltip, {
                tooltip: _t("Drag and drop the building block"),
            });
            setTimeout(this.hideSnippetToolTip, 1500);
        }
    }

    // TODO bounce animation on click if empty editable
}
