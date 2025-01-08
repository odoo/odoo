import { describe, expect, test } from "@odoo/hoot";

import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.header_top");
describe.current.tags("interaction_dev");

const headerTemplate = `<header id="top"></header>`;

test("header_top is started when there is an element header#top", async () => {
    const { core } = await startInteractions(headerTemplate);
    expect(core.interactions).toHaveLength(1);
});
