import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";

describe.current.tags("desktop");

test("section with containers should not be contenteditable, but there containers should, unless outside o_editable", async () => {
    await setupHTMLBuilder(
        `<section><div class="container"><span class="inside">in</span></div></section>`,
        {
            headerContent: `<section><div class="container"><span class="outside">out</span></div></section>`,
        }
    );
    expect(":iframe section:has(.inside)").toHaveProperty("isContentEditable", false);
    expect(":iframe .inside").toHaveProperty("isContentEditable", true);

    expect(":iframe section:has(.outside)").toHaveProperty("isContentEditable", false);
    expect(":iframe .outside").toHaveProperty("isContentEditable", false);
});
