import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";

export class ChecklistIdsPlugin extends Plugin {
    handleCommand(command, payload) {
        switch (command) {
            case "NORMALIZE":
                this.normalize(payload.node);
                break;
        }
    }
    normalize(nodeToSanitize) {
        const block = closestBlock(nodeToSanitize);
        if (!block) {
            return nodeToSanitize;
        }

        // Ensure unique ids on checklists and stars.
        const elementsWithId = [...block.querySelectorAll("[data-check-id]")];
        const maxId = Math.max(
            ...[
                0,
                ...elementsWithId.map((node) => +node.getAttribute("data-check-id").substring(8)),
            ]
        );
        let nextId = maxId + 1;
        const ids = [];
        // todo: make it configurable (at least for o_stars)?
        for (const node of block.querySelectorAll("[data-check-id], .o_checklist > li, .o_stars")) {
            if (
                !node.classList.contains("o_stars") &&
                (!node.parentElement.classList.contains("o_checklist") ||
                    [...node.children].some((child) => ["UL", "OL"].includes(child.nodeName)))
            ) {
                // Remove unique ids from checklists and stars from elements
                // that are no longer checklist items or stars, and from
                // parents of nested lists.
                node.removeAttribute("data-check-id");
            } else {
                // Add/change IDs where needed, and ensure they're unique.
                let id = node.getAttribute("data-check-id");
                if (!id || ids.includes(id)) {
                    id = `${nextId}`;
                    nextId++;
                    node.setAttribute("data-check-id", nextId);
                }
                ids.push(id);
            }
        }

        return nodeToSanitize;
    }
}
