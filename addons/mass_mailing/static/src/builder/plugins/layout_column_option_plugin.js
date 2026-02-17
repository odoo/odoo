import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";

export class MassMailingLayoutColumnPlugin extends Plugin {
    static id = "mass_mailing.LayoutColumnPlugin";
    resources = {
        mark_color_level_selector_params: [{ selector: ".o_mail_snippet_general" }],
        normalize_handlers: this.normalize.bind(this),
    };

    normalize(element) {
        const emptyRowCandidates = element.querySelectorAll(".container > .row:not(:has(> *))");
        const emptyContainerCandidates = new Set();
        const emptySectionCandidates = new Set();

        for (const emptyRowCandidate of emptyRowCandidates) {
            if (isEmptyBlock(emptyRowCandidate)) {
                emptyContainerCandidates.add(emptyRowCandidate.parentElement);
                emptyRowCandidate.remove();
            }
        }
        for (const emptyContainerCandidate of emptyContainerCandidates) {
            if (isEmptyBlock(emptyContainerCandidate)) {
                const section = closestElement(emptyContainerCandidate, "section");
                if (section) {
                    emptySectionCandidates.add(section);
                }
                emptyContainerCandidate.remove();
            }
        }
        for (const emptySectionCandidate of emptySectionCandidates) {
            if (isEmptyBlock(emptySectionCandidate)) {
                emptySectionCandidate.remove();
            }
        }
    }
}

registry
    .category("mass_mailing-plugins")
    .add(MassMailingLayoutColumnPlugin.id, MassMailingLayoutColumnPlugin);
