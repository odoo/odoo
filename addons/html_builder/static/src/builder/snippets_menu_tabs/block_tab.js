import { Component, markup } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { RPCError } from "@web/core/network/rpc";
import { useDraggable } from "@web/core/utils/draggable";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";
import { AddSnippetDialog } from "../add_snippet_dialog/add_snippet_dialog";

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
    static props = {
        snippetModel: { type: Object },
    };

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.company = useService("company");

        const copyOnDrag = copyElementOnDrag();
        useDraggable({
            ref: this.env.builderRef,
            elements: ".o-website-snippetsmenu .o_draggable",
            enable: () => this.env.editor?.isReady,
            iframeWindow: this.env.editor?.editable.ownerDocument.defaultView,
            onWillStartDrag: ({ element }) => {
                copyOnDrag.clone(element);
            },
            onDragStart: ({ element }) => {
                copyOnDrag.insert();
                const { category } = element.dataset;
                const selector = category === "snippet_groups" ? "section" : "p, img";
                this.dropzonePlugin.displayDropZone(selector);
            },
            onDrag: ({ element }) => {
                this.dropzonePlugin.dragElement(element);
            },
            onDrop: ({ element }) => {
                const { x, y, height, width } = element.getClientRects()[0];
                const position = { x, y, height, width };
                const { category, id } = element.dataset;
                const snippet = this.props.snippetModel.getSnippet(category, id);
                if (category === "snippet_groups") {
                    this.openSnippetDialog(snippet, position);
                    return;
                }
                const addElement = this.dropzonePlugin.getAddElement(position);
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
            this.dropzonePlugin.displayDropZone("section");
        }
        const addElement = this.dropzonePlugin.getAddElement(position);
        this.dialog.add(
            AddSnippetDialog,
            {
                selectedSnippet: snippet,
                snippetModel: this.props.snippetModel,
                selectSnippet: (snippet) => {
                    addElement(snippet.content.cloneNode(true));
                },
                installModule: this.onClickInstall.bind(this),
            },
            {
                onClose: () => this.dropzonePlugin.clearDropZone(),
            }
        );
    }

    onClickInstall(snippet) {
        // TODO: Should be the app name, not the snippet name ... Maybe both ?
        const bodyText = _t("Do you want to install %s App?", snippet.title);
        const linkText = _t("More info about this app.");
        const linkUrl =
            "/odoo/action-base.open_module_tree/" + encodeURIComponent(snippet.moduleId);

        this.dialog.add(ConfirmationDialog, {
            title: _t("Install %s", snippet.title),
            body: markup(
                `${escape(bodyText)}\n<a href="${linkUrl}" target="_blank">${escape(linkText)}</a>`
            ),
            confirm: async () => {
                try {
                    await this.orm.call("ir.module.module", "button_immediate_install", [
                        [Number(snippet.moduleId)],
                    ]);
                    // TODO Need to Reload webclient
                    // this._onSaveRequest({
                    //     data: {
                    //         reloadWebClient: true,
                    //     },
                    // });
                } catch (e) {
                    if (e instanceof RPCError) {
                        const message = escape(_t("Could not install module %s", snippet.title));
                        this.notification.add(message, {
                            type: "danger",
                            sticky: true,
                        });
                        return;
                    }
                    throw e;
                }
            },
            confirmLabel: _t("Save and Install"),
            cancel: () => {},
        });
    }
}
