import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { GenerateContentAndCopyButton } from "@hr_recruitment/js/buttons/generate_content_and_copy_button";

defineMailModels();

test("copies the generated content to the clipboard", async () => {
    patchWithCleanup(navigator.clipboard, {
        async writeText(text) {
            expect.step(`writeText: ${text}`);
        },
    });
    await mountWithCleanup(GenerateContentAndCopyButton, {
        props: {
            contentGenerationFunction: async () => {
                expect.step("generate");
                return "jobs+linkedin@example.com";
            },
        },
    });
    await click(".o_clipboard_button");
    await animationFrame();
    expect.verifySteps(["generate", "writeText: jobs+linkedin@example.com"]);
});
