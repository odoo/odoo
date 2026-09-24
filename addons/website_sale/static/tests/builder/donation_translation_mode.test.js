import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupSidebarBuilderForTranslation,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("donation descriptions should be visible in translation mode", async () => {
    await setupSidebarBuilderForTranslation({
        loadIframeBundles: true,
        websiteContent: `
            <div class="s_donation">
                <div class="s_donation_form">
                    <div id="s_donation_description_inputs" class="d-none">
                        <input type="hidden" class="o_translatable_input_hidden" 
                            value="&lt;span data-oe-translation-source-sha=&quot;a1789b026d9a59718b38b96cbde27f90e54bbceb006e51105112680c22cceb68&quot;&gt;A year of cultural awakening.&lt;/span&gt;">
                        <input type="hidden" class="o_translatable_input_hidden"
                            value="&lt;span data-oe-translation-source-sha=&quot;6d5dccf359af69b4e0e63ef76072dbe27578cefe808dd17a16a16a96a3aab913&quot;&gt;Caring for a baby for 1 month.&lt;/span&gt;">
                    </div>
                </div>
            </div>
        `,
    });
    expect(":iframe .s_donation #s_donation_description_inputs").toBeVisible();
});
