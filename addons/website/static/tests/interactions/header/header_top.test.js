import { describe, expect, test } from "@odoo/hoot";

import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.header_top");
describe.current.tags("interaction_dev");

const getTemplate = function (options = {}) {
    return `
    <header id="top">
    </header>
    `
}

test("header_top is started when there is an element header#top", async () => {
    const { core } = await startInteractions(getTemplate());
    expect(core.interactions.length).toBe(1);
});
