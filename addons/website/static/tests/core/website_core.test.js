import { expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";

import { onRpc } from "@web/../tests/web_test_helpers";
import { Interaction } from "@website/core/interaction";
import { startInteraction } from "./helpers";

test("wait for translation before starting interactions", async () => {
    const def = new Deferred();
    onRpc("/web/webclient/translations", async () => {
        await def;
    });
    let started = false;

    class Test extends Interaction {
        static selector=".test";

        setup() {
            started = true;
        }
    }
    
    const p = startInteraction(Test, `<div class="test"></div>`);
    await animationFrame();
    expect(started).toBe(false);

    def.resolve();
    await p;
    await animationFrame();
    expect(started).toBe(true);

});
