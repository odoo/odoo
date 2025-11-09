import { mailModels } from "@mail/../tests/mail_test_helpers";
import { animationFrame } from "@odoo/hoot-mock";
import { registry } from "@web/core/registry";
import { buildEditableInteractions } from "@website/core/website_edit_service";
import { setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { Website } from "./mock_server/mock_models/website";
import { WebsiteVisitor } from "./mock_server/mock_models/website_visitor";

export async function switchToEditMode(core) {
    core.stopInteractions();
    const activeInteractions = setupInteractionWhiteList.getWhiteList();
    const unmatchedInteractions = activeInteractions ? new Set(activeInteractions) : new Set();
    const builders = registry.category("public.interactions.edit").getEntries();
    for (const [key, builder] of builders) {
        if (activeInteractions && !activeInteractions.includes(key)) {
            builder.isAbstract = true;
        }
        unmatchedInteractions.delete(key);
    }
    if (unmatchedInteractions.size) {
        throw new Error(`White-listed Interaction does not exist: ${[...unmatchedInteractions]}.`);
    }
    const Interactions = builders.map((builder) => builder[1]);
    const editableInteractions = buildEditableInteractions(Interactions);
    core.activate(editableInteractions);
    await animationFrame();
}

export const websiteModels = {
    ...mailModels,
    Website,
    WebsiteVisitor,
};
