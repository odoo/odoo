import { expect, test } from "@odoo/hoot";

import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import {
    getTemplateWithoutHideOnScroll,
} from "./helpers";

setupInteractionWhiteList("website.header_standard");

test("header_standard is started when there is an element header.o_header_standard", async () => {
    const { core } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_standard"));
    expect(core.interactions.length).toBe(1);
});
