import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, queryFirst, test } from "@odoo/hoot";

setupInteractionWhiteList("website.a11y_new_tab_link");

describe.current.tags("interaction_dev");

test("links with _target='blank' have a sr-only content", async () => {
    const { core } = await startInteractions(`<a href="odoo.com" target="_blank">Odoo</a>`);
    expect(core.interactions).toHaveLength(1);
    expect(queryFirst(".visually-hidden")).toHaveText("(Open in new tab)");
});
