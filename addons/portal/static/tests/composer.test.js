import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import { PortalComposer } from "@portal/interactions/portal_composer";
import { getInteraction, startInteraction } from "@web/../tests/public/helpers";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Deferred } from "@web/core/utils/concurrency";

const composer = `<div class="o_portal_chatter_composer">
    <div class="o_portal_chatter_composer_input"><textarea name="message">Hello</textarea>
        <div class="o_portal_chatter_attachments"></div></div>
    <button class="o_portal_chatter_attachment_btn"></button>
    <input type="file" class="o_portal_chatter_file_input" multiple="multiple"/>
    <button class="o_portal_chatter_composer_btn" data-action="/mail/message/post"></button>
</div>`;

test("overlapping file selections keep Send disabled until both finish", async () => {
    const { core } = await startInteraction(PortalComposer, composer);
    const interaction = getInteraction(core, PortalComposer);
    const first = new Deferred();
    const second = new Deferred();
    patchWithCleanup(interaction, {
        _uploadOne: (file) => (file.name === "one" ? first : second),
    });
    const input = queryOne('input[type="file"]');
    patchWithCleanup(input, { files: [new File(["1"], "one")] });
    const pendingFirst = interaction.onFileInputChange();
    patchWithCleanup(input, { files: [new File(["2"], "two")] });
    const pendingSecond = interaction.onFileInputChange();
    first.resolve();
    await pendingFirst;
    expect(".o_portal_chatter_composer_btn").toHaveProperty("disabled", true);
    second.resolve();
    await pendingSecond;
    expect(".o_portal_chatter_composer_btn").toHaveProperty("disabled", false);
});

test("unexpected upload errors remain visible to the caller", async () => {
    const { core } = await startInteraction(PortalComposer, composer);
    const interaction = getInteraction(core, PortalComposer);
    onRpc("/mail/attachment/upload", () => ({ data: {} }));
    await expect(
        interaction._uploadOne(new File(["data"], "bad.txt")),
    ).rejects.toThrow();
});

test("posting notifies the interaction's bus", async () => {
    const { core } = await startInteraction(PortalComposer, composer);
    const interaction = getInteraction(core, PortalComposer);
    onRpc("/mail/message/post", () => ({ store_data: { posted: true } }));
    interaction.env.bus.addEventListener("reload_chatter_content", (event) => {
        expect(event.detail).toEqual({ posted: true });
        expect.step("reload");
    });
    await interaction.chatterPostMessage("/mail/message/post");
    expect.verifySteps(["reload"]);
});

test("preparing composer options does not mutate the caller", () => {
    const options = { res_id: "42", default_attachment_ids: "[]" };
    const prepared = PortalComposer.prepareOptions(options);
    expect(prepared.res_id).toBe(42);
    expect(prepared.default_attachment_ids).toEqual([]);
    expect(options).toEqual({ res_id: "42", default_attachment_ids: "[]" });
    expect(PortalComposer.prepareOptions().allow_composer).toBe(true);
});

test("empty messages show validation without rejecting the event handler", async () => {
    const { core } = await startInteraction(
        PortalComposer,
        composer.replace(
            '<textarea name="message">Hello</textarea>',
            '<textarea name="message"></textarea><div class="o_portal_chatter_composer_error d-none"></div>',
        ),
    );
    const interaction = getInteraction(core, PortalComposer);
    expect(await interaction.onSubmitButtonClick(null, interaction.sendButtonEl)).toBe(
        false,
    );
    expect("textarea").toHaveClass("border-danger");
    expect(".o_portal_chatter_composer_error").not.toHaveClass("d-none");
});

test("a pending message cannot be posted twice", async () => {
    const { core } = await startInteraction(PortalComposer, composer);
    const interaction = getInteraction(core, PortalComposer);
    const response = new Deferred();
    onRpc("/mail/message/post", () => {
        expect.step("post");
        return response;
    });
    const pending = interaction.onSubmitButtonClick(null, interaction.sendButtonEl);
    const duplicate = interaction.onSubmitButtonClick(null, interaction.sendButtonEl);
    response.resolve({ store_data: {} });
    const results = await Promise.allSettled([pending, duplicate]);
    expect(results[1]).toEqual({ status: "fulfilled", value: false });
    expect.verifySteps(["post"]);
    expect(".o_portal_chatter_composer_btn").toHaveProperty("disabled", false);
});

test("a slow submission restores Send after the click loading delay", async () => {
    const { core } = await startInteraction(PortalComposer, composer);
    const interaction = getInteraction(core, PortalComposer);
    const response = new Deferred();
    onRpc("/mail/message/post", () => response);
    interaction.sendButtonEl.click();
    await advanceTime(500);
    expect(".o_portal_chatter_composer_btn").toHaveProperty("disabled", true);
    response.resolve({ store_data: {} });
    await animationFrame();
    expect(".o_portal_chatter_composer_btn").toHaveProperty("disabled", false);
    expect(".o_portal_chatter_composer_btn .fa-spin").toHaveCount(0);
});

test("a failed upload batch waits for its remaining files before unlocking", async () => {
    const { core } = await startInteraction(PortalComposer, composer);
    const interaction = getInteraction(core, PortalComposer);
    const remaining = new Deferred();
    patchWithCleanup(interaction, {
        _uploadOne: (file) =>
            file.name === "bad"
                ? Promise.reject(new Error("upload failed"))
                : remaining,
    });
    patchWithCleanup(interaction.fileInputEl, {
        files: [new File(["1"], "bad"), new File(["2"], "slow")],
    });
    const batch = interaction.onFileInputChange();
    const checked = expect(batch).rejects.toThrow("upload failed");
    await animationFrame();
    expect(".o_portal_chatter_composer_btn").toHaveProperty("disabled", true);
    remaining.resolve();
    await checked;
    expect(".o_portal_chatter_composer_btn").toHaveProperty("disabled", false);
});

for (const fails of [false, true]) {
    test(`attachment controls are locked during posting and restored after ${fails ? "failure" : "success"}`, async () => {
        const { core } = await startInteraction(PortalComposer, composer);
        const interaction = getInteraction(core, PortalComposer);
        interaction.attachments = [
            { id: 5, state: "pending", name: "file.txt", mimetype: "text/plain" },
        ];
        interaction.updateAttachments();
        const response = new Deferred();
        patchWithCleanup(interaction, { chatterPostMessage: () => response });
        const pending = interaction
            .onSubmitButtonClick(null, interaction.sendButtonEl)
            .then(
                () => "success",
                () => "failure",
            );
        expect(interaction.attachmentButtonEl.disabled).toBe(true);
        expect(interaction.fileInputEl.disabled).toBe(true);
        expect(".o_portal_chatter_attachment_delete").toHaveProperty("disabled", true);
        if (fails) {
            response.reject(new Error("post failed"));
        } else {
            response.resolve({});
        }
        expect(await pending).toBe(fails ? "failure" : "success");
        expect(interaction.attachmentButtonEl.disabled).toBe(false);
        expect(interaction.fileInputEl.disabled).toBe(false);
        expect(".o_portal_chatter_attachment_delete").toHaveProperty("disabled", false);
    });
}

test("ignored file selections during posting are cleared for a later retry", async () => {
    const { core } = await startInteraction(PortalComposer, composer);
    const interaction = getInteraction(core, PortalComposer);
    interaction.isPosting = true;
    const transfer = new DataTransfer();
    transfer.items.add(new File(["late"], "late.txt"));
    interaction.fileInputEl.files = transfer.files;
    await interaction.onFileInputChange();
    expect(interaction.fileInputEl.value).toBe("");
    expect(interaction.fileInputEl.files.length).toBe(0);
});

test("posting preserves attachment controls that were already disabled", async () => {
    const { core } = await startInteraction(PortalComposer, composer);
    const interaction = getInteraction(core, PortalComposer);
    interaction.attachmentButtonEl.disabled = true;
    patchWithCleanup(interaction, { chatterPostMessage: async () => ({}) });
    await interaction.onSubmitButtonClick(null, interaction.sendButtonEl);
    expect(interaction.attachmentButtonEl.disabled).toBe(true);
    expect(interaction.fileInputEl.disabled).toBe(false);
});

test("a composer without attachment controls can still post", async () => {
    const { core } = await startInteraction(
        PortalComposer,
        `<div class="o_portal_chatter_composer">
        <div class="o_portal_chatter_composer_input"><textarea name="message">Hello</textarea></div>
        <button class="o_portal_chatter_composer_btn" data-action="/mail/message/post"></button>
    </div>`,
    );
    const interaction = getInteraction(core, PortalComposer);
    onRpc("/mail/message/post", () => ({ store_data: { posted: true } }));
    expect(
        await interaction.onSubmitButtonClick(null, interaction.sendButtonEl),
    ).toEqual({ posted: true });
    expect(interaction.sendButtonEl.disabled).toBe(false);
});
