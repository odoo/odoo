import { describe, expect, test } from "@odoo/hoot";
import { hover, leave } from "@odoo/hoot-dom";

import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.hoverable_dropdown");
describe.current.tags("interaction_dev");

const getTemplate = function (options = {}) {
    return `
        <header class="o_hoverable_dropdown" style="display: flex; height: 50px; background-color: #CCFFCC;">
            <div class="dropdown" style="margin: auto;">
                <a class="dropdown-toggle">Dropdown</a>
                <div class="dropdown-menu">
                    <a href="#" style="display: block;">A</a>
                    <a href="#" style="display: block;">B</a>
                    <a href="#" style="display: block;">C</a>
                </div>
            </div>
        </header>
    `
}

test("hoverable_dropdown is started when there is an element header.o_hoverable_dropdown", async () => {
    const { core } = await startInteractions(getTemplate());
    expect(core.interactions.length).toBe(1);
});

test.tags("desktop")("[hover] show / hide content", async () => {
    await startInteractions(getTemplate());
    expect(".dropdown-toggle").not.toHaveClass("show");
    expect(".dropdown-menu > a").not.toBeVisible();
    await hover(".dropdown");
    expect(".dropdown-toggle").toHaveClass("show");
    expect(".dropdown-menu > a").toBeVisible();
    await leave(".dropdown");
    expect(".dropdown-toggle").not.toHaveClass("show");
    expect(".dropdown-menu > a").not.toBeVisible();
});
