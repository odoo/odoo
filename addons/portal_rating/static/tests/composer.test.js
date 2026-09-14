import "@portal_rating/interactions/portal_composer";

import { expect, test } from "@odoo/hoot";
import { PortalComposer } from "@portal/interactions/portal_composer";
import { getInteraction, startInteraction } from "@web/../tests/public/helpers";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Modal } from "@web/libs/bootstrap";

const template = `<div id="ratingpopupcomposer" class="modal"><div class="o_portal_chatter_composer">
    <div class="o_portal_chatter_composer_error d-none"></div>
    <div class="o_portal_chatter_composer_input"><textarea name="message"></textarea>
    <div class="o_portal_chatter_attachments"></div></div>
    <input name="rating_value" value="4"/>
    <input type="file" class="o_portal_chatter_file_input"/>
    <button class="o_portal_chatter_attachment_btn"></button>
    <button class="o_portal_chatter_composer_btn" data-action="/mail/message/post"></button>
</div></div>`;

test("an invalid review stays open; a valid retry closes and refreshes", async () => {
    const { core } = await startInteraction(PortalComposer, template);
    const interaction = getInteraction(core, PortalComposer);
    const modal = interaction.el.closest(".modal");
    patchWithCleanup(Modal, {
        getOrCreateInstance: () => ({
            hide() {
                expect.step("hide");
                modal.dispatchEvent(new Event("hidden.bs.modal"));
            },
        }),
    });
    interaction.options.reloadRatingPopupComposer = () => expect.step("refresh");
    onRpc("/mail/message/post", () => {
        expect.step("post");
        return { store_data: {} };
    });
    await interaction.onSubmitButtonClick(null, interaction.sendButtonEl);
    expect.verifySteps([]);
    interaction.inputTextareaEl.value = "Good service";
    await interaction.onSubmitButtonClick(null, interaction.sendButtonEl);
    expect.verifySteps(["post", "hide", "refresh"]);
});
