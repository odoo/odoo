import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { animationFrame, describe, expect, queryAllTexts, queryOne, test } from "@odoo/hoot";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { execCommand } from "@html_editor/../tests/_helpers/userCommands";

defineWebsiteModels();

describe("alert snippet availability in powerbox", () => {
    test("alert snippet should be available from p at root of editable", async () => {
        const { getEditor } = await setupWebsiteBuilder("<p>ab</p>");
        setSelection({ anchorNode: queryOne(":iframe p"), anchorOffset: 0 });
        await insertText(getEditor(), "/alert");
        await animationFrame();
        expect(queryAllTexts(".o-we-command-name")).toInclude("Alert");
    });
    test("alert snippet should not be available from p which is the root of editable", async () => {
        const { getEditor } = await setupWebsiteBuilder(
            '<div contenteditable="false"><p contenteditable="true">ab</p></div>'
        );
        setSelection({ anchorNode: queryOne(":iframe p"), anchorOffset: 0 });
        await insertText(getEditor(), "/alert");
        await animationFrame();
        expect(queryAllTexts(".o-we-command-name")).not.toInclude("Alert");
    });
});

test("should not unwrap s_blockquote when inserting it in unbreakable inline element", async () => {
    const { getEditor } = await setupWebsiteBuilder(
        `<p><span class="oe_unbreakable">ab</span></p>`
    );
    setSelection({ anchorNode: queryOne(":iframe span"), anchorOffset: 0 });
    execCommand(getEditor(), "s_blockquote");
    expect(":iframe span .s_blockquote").toHaveCount(0);
    expect(":iframe .s_blockquote").toHaveCount(1);
});
