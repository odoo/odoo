import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";

setupInteractionWhiteList("public.login");

describe.current.tags("interaction_dev");

test("add and remove loading effect", async () => {
    const { core } = await startInteractions(`
        <div class="oe_login_form">
            <button type="submit">log in</button>
        </div>`);
    expect(core.interactions).toHaveLength(1);
    // Not using manuallyDispatchProgrammaticEvent to keep a minimalist test. We
    // don't need to send a proper "submit" event with FormData, method, action,
    // etc. for this test.
    const ev = new Event("submit");
    queryOne(".oe_login_form").dispatchEvent(ev);
    expect("button").toHaveClass(["o_btn_loading", "disabled"]);
    ev.preventDefault();
    expect("button").not.toHaveClass(["o_btn_loading", "disabled"]);
});
