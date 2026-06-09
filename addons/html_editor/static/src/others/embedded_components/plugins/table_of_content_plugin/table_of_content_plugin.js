import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import {
    HEADINGS,
    TableOfContentManager,
} from "@html_editor/others/embedded_components/core/table_of_content/table_of_content_manager";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { DISABLED_NAMESPACE } from "@html_editor/main/toolbar/toolbar_plugin";

export class TableOfContentPlugin extends Plugin {
    static id = "tableOfContent";
    static dependencies = [
        "dom",
        "selection",
        "embeddedComponents",
        "link",
        "history",
        "domObserver",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "insertTableOfContent",
                title: _t("Table of Contents"),
                description: _t("Highlight the structure (headings)"),
                icon: "fa-bookmark",
                run: this.insertTableOfContent.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        powerbox_items: [
            {
                categoryId: "navigation",
                commandId: "insertTableOfContent",
            },
        ],

        /** Handlers */
        on_savepoint_restored_handlers: () => this.delayedUpdateTableOfContents(this.editable),
        on_will_reset_history_handlers: () => this.delayedUpdateTableOfContents(this.editable),
        on_history_rebased_handlers: () => this.delayedUpdateTableOfContents(this.editable),
        on_committed_to_history_handlers: (commit) => {
            const root =
                this.dependencies.domObserver.getMutationsCommonAncestor(
                    commit.data.mutations || []
                ) || this.editable;
            return this.delayedUpdateTableOfContents(root);
        },
        on_remote_history_commits_applied_handlers: this.delayedUpdateTableOfContents.bind(
            this,
            this.editable
        ),
        on_will_mount_component_handlers: this.setupNewToc.bind(this),

        /** Processors */
        clean_for_save_processors: this.cleanForSave.bind(this),

        toolbar_namespace_providers: withSequence(70, (targetedNodes) => {
            if (
                targetedNodes.length &&
                targetedNodes.every((node) =>
                    closestElement(node, `[data-embedded="tableOfContent"]`)
                )
            ) {
                return DISABLED_NAMESPACE;
            }
        }),

        system_classes: ["o_embedded_toc_header_highlight"],
    };

    setup() {
        this.manager = new TableOfContentManager({ el: this.editable });
        this.alive = true;
        this.manager.batchedUpdateStructure();
    }

    insertTableOfContent() {
        const tableOfContentBlueprint = renderToElement("html_editor.TableOfContentBlueprint");
        this.dependencies.dom.insert(tableOfContentBlueprint);
        this.dependencies.history.commit();
    }

    /**
     * @param {HTMLElement} root
     */
    cleanForSave(root) {
        for (const el of root.querySelectorAll(".o_embedded_toc_header_highlight")) {
            el.classList.remove("o_embedded_toc_header_highlight");
        }
        return root;
    }

    destroy() {
        super.destroy();
        this.alive = false;
    }

    delayedUpdateTableOfContents(element) {
        const selector = HEADINGS.join(",");
        if (
            !(
                !element ||
                this.manager.structure.headings.length ||
                element.querySelector(selector) ||
                element.closest(selector)
            )
        ) {
            return;
        }
        if (this.updateTimeout) {
            window.clearTimeout(this.updateTimeout);
        }
        this.updateTimeout = window.setTimeout(() => {
            if (!this.alive) {
                return;
            }
            this.manager.updateStructure();
        }, 500);
    }

    setupNewToc({ name, props }) {
        if (name === "tableOfContent") {
            Object.assign(props, {
                manager: this.manager,
            });
        }
    }
}
