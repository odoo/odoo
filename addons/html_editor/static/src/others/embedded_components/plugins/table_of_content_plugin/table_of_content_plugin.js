import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import {
    HEADINGS,
    TableOfContentManager,
} from "@html_editor/others/embedded_components/core/table_of_content/table_of_content_manager";

export class TableOfContentPlugin extends Plugin {
    static name = "tableOfContent";
    static dependencies = ["dom", "selection", "embedded_components", "link", "history"];
    resources = {
        user_commands: [
            {
                id: "insertTableOfContent",
                label: _t("Table Of Content"),
                description: _t("Highlight the structure (headings) of this field"),
                icon: "fa-bookmark",
                run: this.insertTableOfContent.bind(this),
            },
        ],
        powerboxItems: [
            {
                category: "navigation",
                commandId: "insertTableOfContent",
            },
        ],
        mutation_filtered_classes: ["o_embedded_toc_header_highlight"],
        restore_savepoint_listeners: this.delayedUpdateTableOfContents.bind(this),
        history_reseted_listeners: () => this.delayedUpdateTableOfContents(),
        history_reseted_from_steps_listeners: this.delayedUpdateTableOfContents.bind(this),
        step_added_listeners: ({ stepCommonAncestor }) =>
            this.delayedUpdateTableOfContents(stepCommonAncestor),
        external_step_added_listeners: this.delayedUpdateTableOfContents.bind(this),
        clean_for_save_listeners: this.cleanForSave.bind(this),
        mount_component_listeners: this.setupNewToc.bind(this),
    };

    setup() {
        this.manager = new TableOfContentManager({
            el: this.editable,
        });
        this.alive = true;
    }

    insertTableOfContent() {
        const tableOfContentBlueprint = renderToElement("html_editor.TableOfContentBlueprint");
        this.shared.domInsert(tableOfContentBlueprint);
        this.shared.addStep();
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
