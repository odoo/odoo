import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { Component, onWillStart, xml } from "@odoo/owl";
import { useSnippets } from "@html_builder/snippets/snippet_service";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";
import { IrUiView, ResCompany } from "@mass_mailing/../tests/mass_mailing_test_helpers";

defineMailModels();

patchWithCleanup(ResCompany.prototype, {
    get_mailing_snippet_info() {
        expect.step("mailing snippet info");
        return super.get_mailing_snippet_info();
    },
});

defineModels([IrUiView, ResCompany]);

describe.current.tags("desktop");

/**
 * Test that the mailing snippet model functions as it should.
 * As snippets are no longer stored as views in the backend but rather injected in the file received by
 * a call to "render_public_asset" before being treated by the snippet model,
 * we check that our mailings snippets do exist and have been populated with the relevant data.
 */
describe("mailing snippet model", () => {
    let snippetService = {};

    class IframeCmp extends Component {
        async setup() {
            this.snippetService = useSnippets("mass_mailing.email_designer_snippets");
            this.snippetService.load();
            snippetService = this.snippetService;
            onWillStart(async () => {
                await this.snippetService.loadProm;
            });
        }
        static template = xml`
            <div></div>
        `;
    }
    beforeEach(async () => {
        snippetService = {};
        await mountWithCleanup(IframeCmp);
        await snippetService.loadProm;
    });

    test("snippets can be found in snippet model", async () => {
        expect.verifySteps(["mailing snippet info"]);
        expect(
            snippetService.getSnippetByName(
                "snippet_structure",
                "s_mail_block_footer_social_and_logo"
            )
        ).not.toBe(undefined);
        expect(
            snippetService.getSnippetByName("snippet_structure", "s_mail_block_header_social")
        ).not.toBe(undefined);
        expect(snippetService.getSnippetByName("snippet_content", "s_inline_text")).not.toBe(
            undefined
        );
        expect(snippetService.getSnippetByName("snippet_content", "s_hr")).not.toBe(undefined);
        // sanity check: missing snippets should be undefined
        expect(snippetService.getSnippetByName("snippet_content", "s_nonexistent_snippet")).toBe(
            undefined
        );
    });

    test("backend custom snippets are linked to their origin frontend snippets", async () => {
        expect.verifySteps(["mailing snippet info"]);
        // Create a backend snippet and reload
        const snippetEl = snippetService.getSnippetByName(
            "snippet_structure",
            "s_masonry_block"
        ).content;
        snippetEl.querySelector("p").innerText = "This is our custom snippet text!";
        snippetEl.dataset.name = "Snippet Named Bob";
        await snippetService.saveSnippet(snippetEl, []);
        expect.verifySteps(["mailing snippet info"]);

        // Check that the custom snippet exists and that its content is equivalent to the snippet we just saved
        const savedCustomSnippet = snippetService.getSnippetByName(
            "snippet_custom",
            "s_masonry_block"
        );
        expect(savedCustomSnippet.title).toBe("Custom Snippet Named Bob");
        expect(savedCustomSnippet.content.innerHTML).toBe(snippetEl.innerHTML);
    });

    test("Owl & templates accurately pass down context information to social & logo subtemplates for rendering", async () => {
        expect.verifySteps(["mailing snippet info"]);
        const blockSocialAndLogo = snippetService.getSnippetByName(
            "snippet_structure",
            "s_mail_block_footer_social_and_logo"
        ).content;

        // check socials presence
        expect(
            blockSocialAndLogo.querySelector(
                "a[href='https://example.com/testLinkFacebook'][data-platform='facebook']"
            )
        ).not.toBe(undefined);
        expect(
            blockSocialAndLogo.querySelector(
                "a[href='https://example.com/testLinkTwitter'][data-platform='twitter']"
            )
        ).not.toBe(undefined);
        expect(
            blockSocialAndLogo.querySelector(
                "a[href='https://www.linkedin.com/company/odoo'][data-platform='linkedin']"
            )
        ).not.toBe(undefined);

        // check logo presence
        const companyId = user.activeCompany.id;
        expect(
            blockSocialAndLogo.querySelector(`img[src='/web/image/res.company/${companyId}/logo']`)
        ).not.toBe(undefined);
    });
});
