import { expect, test } from "@odoo/hoot";

import {
    startInteractions,
    setupInteractionWhiteList,
} from "../../core/helpers";

import {
    getTemplateWithoutHideOnScroll,
} from "./helpers";

setupInteractionWhiteList("website.header_disappears");

test("header_disappears is started when there is an element header.o_header_disappears", async () => {
    const { core } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_disappears"));
    expect(core.interactions.length).toBe(1);
});
