import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";

setupInteractionWhiteList("website.a11y_new_tab_link");

describe.current.tags("interaction_dev");

test("links with _target='blank' have a visually-hidden indicator", async () => {
    const { core } = await startInteractions(
        `<div>
            <a id="link1" href="odoo.com" target="_blank">Odoo</a>
            <a id="link2" href="odoo.com">Odoo</a>
        </div>`
    );

    expect(core.interactions).toHaveLength(1);
    expect("#link1").toHaveText("Odoo\n(Open in new tab)");
    expect("#link2").toHaveText("Odoo");

    core.stopInteractions();
    expect("#link1").toHaveText("Odoo");
});

test("links with _target='blank' and aria-label have an indicator in the aria-label", async () => {
    const { core } = await startInteractions(
        `<div>
            <a id="link1" href="odoo.com" target="_blank" aria-label="Go to homepage"><i class="oi" data-icon="home"></i></a>
            <a id="link2" href="odoo.com" aria-label="Go to homepage"><i class="oi" data-icon="home"/></i></a>
            <a id="link3" href="odoo.com" target="_blank" aria-label=""><i class="oi" data-icon="home"></i></a>
        </div>`
    );
    expect(core.interactions).toHaveLength(2);
    expect("#link1").toHaveAttribute("aria-label", "Go to homepage (Open in new tab)");
    expect("#link2").toHaveAttribute("aria-label", "Go to homepage");

    core.stopInteractions();
    expect("#link1").toHaveAttribute("aria-label", "Go to homepage");
    expect("#link3").toHaveAttribute("aria-label", "");
});
