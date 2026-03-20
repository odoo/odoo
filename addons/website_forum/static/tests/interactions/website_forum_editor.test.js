import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { WebsiteForumWysiwyg } from "../../src/components/website_forum_wysiwyg/website_forum_wysiwyg";
import { onMounted } from "@odoo/owl";

setupInteractionWhiteList(["website_forum.website_forum"]);

const makeHtmlContent = (karma) => `
    <div id="wrapwrap" class="website_forum">
        <form>
            <div class="o_wysiwyg_textarea_wrapper">
                <textarea class="o_wysiwyg_loader" content="abc" data-karma="0"></textarea>
            </div>
            <input type="hidden" id="karma" value="${karma}"></input>
            <button type="submit">Submit</button>
        </form>
    </div>
`;

describe("editor in forum", () => {
    let mountedWysiwyg;
    beforeEach(() => {
        mountedWysiwyg = new Promise((resolve) => {
            patchWithCleanup(WebsiteForumWysiwyg.prototype, {
                setup() {
                    super.setup();
                    onMounted(() => resolve(this));
                },
            });
        });
    });
    test("Can instantiate the forum wysiwyg in full edit mode", async () => {
        const { core } = await startInteractions(makeHtmlContent(1));
        expect(core.interactions).toHaveLength(1);
        const wysiwyg = await mountedWysiwyg;
        expect(".note-editable").toHaveCount(1);
        expect(wysiwyg.props.fullEdit).toBe(true);
    });
    test("Can instantiate the forum wysiwyg without full edit mode", async () => {
        const { core } = await startInteractions(makeHtmlContent(-1));
        expect(core.interactions).toHaveLength(1);
        const wysiwyg = await mountedWysiwyg;
        expect(".note-editable").toHaveCount(1);
        expect(wysiwyg.props.fullEdit).toBe(false);
    });
    test("H1 to H3 are not available as fonts", async () => {
        await startInteractions(makeHtmlContent(1));
        const wysiwyg = await mountedWysiwyg;
        const fontPlugin = wysiwyg.editor.plugins.find((p) => p.constructor.id === "font");
        const tagNames = fontPlugin.availableFontItems.map((item) => item.tagName);
        expect(tagNames).not.toInclude("h1");
        expect(tagNames).not.toInclude("h2");
        expect(tagNames).not.toInclude("h3");
    });
});
