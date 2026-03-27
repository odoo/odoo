import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import {
    HEADINGS,
    TableOfContentManager,
} from "@html_editor/others/embedded_components/core/table_of_content/table_of_content_manager";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

export class TableOfContentPlugin extends Plugin {
    static id = "tableOfContent";
    static dependencies = ["dom", "selection", "embeddedComponents", "link", "history"];
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
        restore_savepoint_handlers: () => this.delayedUpdateTableOfContents(this.editable),
        history_reset_handlers: () => this.delayedUpdateTableOfContents(this.editable),
        history_reset_from_steps_handlers: () => this.delayedUpdateTableOfContents(this.editable),
        step_added_handlers: ({ stepCommonAncestor }) =>
            this.delayedUpdateTableOfContents(stepCommonAncestor),
        external_step_added_handlers: this.delayedUpdateTableOfContents.bind(this, this.editable),
        clean_for_save_handlers: this.cleanForSave.bind(this),
        mount_component_handlers: this.setupNewToc.bind(this),

        system_classes: ["o_embedded_toc_header_highlight"],
    };

    setup() {
        this.manager = new TableOfContentManager({
            el: this.editable,
        });
        this.alive = true;
    }

    insertTableOfContent() {
        const tableOfContentBlueprint = renderToElement("html_editor.TableOfContentBlueprint");
        this.dependencies.dom.insert(tableOfContentBlueprint);
        this.dependencies.history.addStep();
    }

    /**
     * @param {HTMLElement} root
     */
    cleanForSave({ root }) {
        for (const el of root.querySelectorAll(".o_embedded_toc_header_highlight")) {
            el.classList.remove("o_embedded_toc_header_highlight");
        }
    }

    destroy() {
        super.destroy();
        this.alive = false;
    }

    delayedUpdateTableOfContents(element) {
        const selector = HEADINGS.join(",");
        if (!(!element || element.querySelector(selector) || element.closest(selector))) {
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
