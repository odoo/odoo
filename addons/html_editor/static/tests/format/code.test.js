import { waitFor } from "@odoo/hoot-dom";
import { setupEditor } from "../_helpers/editor";
import { expect, test } from "@odoo/hoot";
import { expandToolbar } from "../_helpers/toolbar";

test("should have toolbar within code block", async () => {
    await setupEditor(`<pre>ab[cde]fg</pre>`);
    await waitFor(".o-we-toolbar");
    expect(".btn[name='font']").toHaveCount(1);
    expect(".btn[name='bold']").toHaveCount(1);
    expect(".btn[name='link']").toHaveCount(1);
    expect(".btn[name='translate']").toHaveCount(0);
    await expandToolbar("codeexpanded");
    expect(".btn[name='font']").toHaveCount(1);
    expect(".btn[name='bold']").toHaveCount(1);
    expect(".btn[name='link']").toHaveCount(1);
    expect(".btn[name='translate']").toHaveCount(1);
});
