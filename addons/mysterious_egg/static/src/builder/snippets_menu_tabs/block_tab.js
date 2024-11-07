import { Component, markup, onWillStart, useState } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { RPCError } from "@web/core/network/rpc";
import { useDraggable } from "@web/core/utils/draggable";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";
import { AddSnippetDialog } from "../add_snippet_dialog/add_snippet_dialog";
import { SnippetModel } from "../snippet_model";

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
    static template = "mysterious_egg.BlockTab";

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.company = useService("company");

        this.snippetModel = useState(
            new SnippetModel(this.env.services, {
                websiteId: this.props.websiteId,
                snippetsName: this.props.snippetsName,
            })
        );
        onWillStart(async () => {
            await this.snippetModel.load();
        });
        const copyOnDrag = copyElementOnDrag();
        useDraggable({
            ref: this.env.builderRef,
            elements: ".o-website-snippetsmenu .o_draggable",
            enable: () => this.props.editor?.isReady,
            onWillStartDrag: ({ element }) => {
                copyOnDrag.clone(element);
            },
            onDragStart: () => {
                copyOnDrag.insert();
                this.props.editor.shared.displayDropZone("p, img");
            },
            onDrag: ({ element }) => {
                this.props.editor.shared.dragElement(element);
            },
            onDrop: ({ element }) => {
                const { x, y, height, width } = element.getClientRects()[0];
                const { category, id } = element.dataset;
                const snippet = this.getSnippet(category, id);
                this.props.editor.shared.dropElement(snippet.content.cloneNode(true), {
                    x,
                    y,
                    height,
                    width,
                });
            },
            onDragEnd: () => {
                copyOnDrag.clean();
            },
        });
    }

    get innerContentSnippets() {
        return this.snippetModel.snippetsByCategory.snippet_content;
    }

    getSnippet(category, id) {
        return this.snippetModel.snippetsByCategory[category].filter(
            (snippet) => snippet.id === id
        )[0];
    }

    openSnippetDialog(snippet) {
        this.props.editor.shared.displayDropZone("section");

        this.dialog.add(
            AddSnippetDialog,
            {
                selectedSnippet: snippet,
                snippetModel: this.snippetModel,
                selectSnippet: (snippet) => {
                    this.props.editor.shared.addElementToCenter(snippet.content.cloneNode(true));
                },
            },
            {
                onClose: () => this.props.editor.shared.clearDropZone(),
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
                        [snippet.moduleID],
                    ]);
                    this.invalidateSnippetCache = true;

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
