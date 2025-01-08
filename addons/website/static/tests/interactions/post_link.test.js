import {
    mockSendRequests,
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.post_link");

describe.current.tags("interaction_dev");

test("post_link adds and removes class on setup/destroy", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <span data-post="/some/url" class="post_link">All</span>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    expect("span").toHaveClass("o_post_link_js_loaded");
    core.stopInteractions();
    expect(core.interactions).toHaveLength(0);
    expect("span").not.toHaveClass("o_post_link_js_loaded");
});

test("post_link handle clicks by sending a request", async () => {
    const requests = mockSendRequests();
    await startInteractions(`
        <div id="wrapwrap">
            <span data-post="/some/url" class="post_link">All</span>
        </div>
    `);
    expect(requests).toEqual([]);
    click("span");
    await animationFrame();
    expect(requests).toEqual([{ url: "/some/url", method: "POST" }]);
});
