import { Component, markup, onWillStart } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { RPCError } from "@web/core/network/rpc";
import { useDraggable } from "@web/core/utils/draggable";
import { uniqueId } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";

const cacheSnippetTemplate = {};

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

        onWillStart(async () => {
            this.snippetsByCategory = await this.loadSnippets();
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
            onDrop: (params) => {
                const { x, y } = params;
                const { category, id } = params.element.dataset;
                const snippet = this.getSnippet(category, parseInt(id));
                this.props.editor.shared.dropElement(snippet.content.cloneNode(true), { x, y });
            },
            onDragEnd: ({ element }) => {
                copyOnDrag.clean();
            },
        });
    }

    get snippetCategories() {
        return this.snippetsByCategory.snippet_groups;
    }

    get innerContentSnippets() {
        return this.snippetsByCategory.snippet_content;
    }

    getSnippet(category, id) {
        return this.snippetsByCategory[category].filter((snippet) => snippet.id === id)[0];
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

    async loadSnippets() {
        if (!cacheSnippetTemplate[this.props.snippetsName]) {
            cacheSnippetTemplate[this.props.snippetsName] = this.orm.silent.call(
                "ir.ui.view",
                "render_public_asset",
                [this.props.snippetsName, {}],
                { context: { rendering_bundle: true } }
            );
        }
        const html = await cacheSnippetTemplate[this.props.snippetsName];
        const snippetsDocument = new DOMParser().parseFromString(html, "text/html");
        return this.computeSnippetTemplates(snippetsDocument);
    }

    computeSnippetTemplates(snippetsDocument) {
        const snippetsBody = snippetsDocument.body;
        const snippetsByCategory = {};
        for (const snippetCategory of snippetsBody.querySelectorAll("snippets")) {
            const snippets = [];
            for (const snippetEl of snippetCategory.children) {
                const snippet = {
                    title: snippetEl.getAttribute("name"),
                    thumbnailSrc: escape(snippetEl.dataset.oeThumbnail),
                };
                const moduleId = snippetEl.dataset.moduleId;
                if (moduleId) {
                    Object.assign(snippet, {
                        id: uniqueId(moduleId),
                        moduleId,
                    });
                } else {
                    Object.assign(snippet, {
                        id: parseInt(snippetEl.dataset.oeSnippetId),
                        content: snippetEl.children[0],
                    });
                }
                snippets.push(snippet);
            }
            snippetsByCategory[snippetCategory.id] = snippets;
        }

        return snippetsByCategory;
    }
}
