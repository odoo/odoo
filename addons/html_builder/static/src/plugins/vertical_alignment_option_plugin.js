import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";

export class VerticalAlignmentOptionPlugin extends Plugin {
    static id = "verticalAlignmentOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_actions: {
            SetVerticalAlignmentAction,
        },
    };

    setup() {
        this.upgradeContainers();
    }

    // TODO: Remove once data-vxml="number" snippet comparison is restored.
    upgradeContainers() {
        // Upgrade legacy card snippets for visual consistency on new versions.
        const snippetEls = this.document.querySelectorAll(
            ".s_cards_soft:not([data-vxml]), .s_cards_grid:not([data-vxml])"
        );

        for (const snippetEl of snippetEls) {
            // Handle all cards inside the section
            for (const cardEl of snippetEl.querySelectorAll(".s_card")) {
                const rowEl = cardEl.closest(".row");
                // Preserve top alignment for cards that originally lacked h-100
                if (!rowEl?.classList.contains("align-items-start")) {
                    rowEl.classList.add("align-items-start");
                }

                // Ensure each card stretches fully
                cardEl.classList.add("h-100");

                // Additional handling for .s_cards_grid
                if (snippetEl.classList.contains("s_cards_grid")) {
                    const colAncestor = cardEl.closest("[class*='col-']");
                    if (colAncestor) {
                        colAncestor.classList.add("d-flex", "flex-column");
                    }

                    const cardImg = cardEl.querySelector(".o_card_img, img");
                    if (cardImg) {
                        cardImg.classList.add("object-fit-cover");
                    }
                }
            }

            // Once all cards in this section are updated, mark it as vxml 001
            snippetEl.dataset.vxml = "001";
        }
    }
}

export class SetVerticalAlignmentAction extends ClassAction {
    static id = "setVerticalAlignment";
    getPriority({ params: { mainParam: classNames } = { mainParam: "" } }) {
        return classNames === "align-items-stretch" ? 0 : 1;
    }
    isApplied({ params: { mainParam: classNames } }) {
        if (classNames === "align-items-stretch") {
            return true;
        }
        return super.isApplied(...arguments);
    }
}

registry
    .category("builder-plugins")
    .add(VerticalAlignmentOptionPlugin.id, VerticalAlignmentOptionPlugin);
