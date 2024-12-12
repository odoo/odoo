import { animationFrame } from "@odoo/hoot-mock";
import { registry } from "@web/core/registry";
import { buildEditableInteractions } from "@website/core/website_edit_service";

let activeInteractions = null;

export async function switchToEditMode(core) {
    core.stopInteractions();
    const unmatchedInteractions = activeInteractions ? new Set(activeInteractions) : new Set();
    const builders = registry
        .category("website.editable_active_elements_builders")
        .getEntries();
    for (const [key, builder] of builders) {
        if (activeInteractions && !activeInteractions.includes(key)) {
            builder.isAbstract = true;
        }
        unmatchedInteractions.delete(key);
    }
    if (unmatchedInteractions.size) {
        throw new Error(
            `White-listed Interaction does not exist: ${[...unmatchedInteractions]}.`
        );
    }
    const Interactions = builders.map((builder) => builder[1]);
    const editableInteractions = buildEditableInteractions(Interactions);
    core.activate(editableInteractions);
    await animationFrame();
}
