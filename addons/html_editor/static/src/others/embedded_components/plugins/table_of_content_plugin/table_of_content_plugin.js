import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import {
    HEADINGS,
    TableOfContentManager,
} from "@html_editor/others/embedded_components/core/table_of_content/table_of_content_manager";

export class TableOfContentPlugin extends Plugin {
    static name = "tableOfContent";
    static dependencies = ["dom", "selection", "embedded_components", "link"];
    resources = {
        powerboxItems: [
            {
                category: "navigation",
                name: _t("Table Of Content"),
                description: _t("Highlight the structure (headings) of this field"),
                fontawesome: "fa-bookmark",
                action: () => {
                    this.insertTableOfContent();
                },
            },
        ],
        mutation_filtered_classes: ["o_embedded_toc_header_highlight"],
        onExternalHistorySteps: this.delayedUpdateTableOfContents.bind(this, this.editable),
    };

    setup() {
        this.manager = new TableOfContentManager({
            el: this.editable,
        });
        this.alive = true;
    }

    /**
     * @param {string} command
     * @param {Object} payload
     */
    handleCommand(command, payload) {
        switch (command) {
            case "CLEAN_FOR_SAVE":
                this.cleanForSave(payload.root);
                break;
            case "RESTORE_SAVEPOINT":
            case "HISTORY_RESET_FROM_STEPS":
            case "HISTORY_RESET":
                this.delayedUpdateTableOfContents(this.editable);
                break;
            case "STEP_ADDED":
                this.delayedUpdateTableOfContents(payload.stepCommonAncestor);
                break;
            case "SETUP_NEW_COMPONENT":
                this.setupNewToc(payload);
                break;
        }
    }

    insertTableOfContent() {
        const tableOfContentBlueprint = renderToElement("html_editor.TableOfContentBlueprint");
        this.shared.domInsert(tableOfContentBlueprint);
        this.dispatch("ADD_STEP");
    }

    /**
     * @param {HTMLElement} root
     */
    cleanForSave(root) {
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
