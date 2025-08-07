import { expect, test } from "@odoo/hoot";
import { setupHTMLBuilder } from "./helpers";
import { markup } from "@odoo/owl";

test("section with containers should not be contenteditable, but there containers should, unless outside o_editable", async () => {
    await setupHTMLBuilder(
        markup`<section><div class="container"><span class="inside">in</span></div></section>`,
        {
            headerContent: markup`<section><div class="container"><span class="outside">out</span></div></section>`,
        }
    );
    expect(":iframe section:has(.inside)").toHaveProperty("isContentEditable", false);
    expect(":iframe .inside").toHaveProperty("isContentEditable", true);

    expect(":iframe section:has(.outside)").toHaveProperty("isContentEditable", false);
    expect(":iframe .outside").toHaveProperty("isContentEditable", false);
});
