import { describe, expect, test } from "@odoo/hoot";

import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import {
    getTemplateWithoutHideOnScroll,
} from "./helpers";

setupInteractionWhiteList("website.header_disappears");
describe.current.tags("interaction_dev");

test("header_disappears is started when there is an element header.o_header_disappears", async () => {
    const { core } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_disappears"));
    expect(core.interactions.length).toBe(1);
});
