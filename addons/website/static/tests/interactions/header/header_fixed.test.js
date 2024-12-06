import { expect, test } from "@odoo/hoot";

import {
    startInteractions,
    setupInteractionWhiteList,
} from "../../core/helpers";

import {
    setupTest,
    checkHeader,
    customScroll,
    getTemplateWithoutHideOnScroll,
    getTemplateWithHideOnScroll,
} from "./helpers";

setupInteractionWhiteList("website.header_fixed");

test("header_fixed is started when there is an element header.o_header_fixed", async () => {
    const { core } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_fixed"));
    expect(core.interactions.length).toBe(1);
});

const behavior1 = {
    visibility: true,
    paddingTop: "",
    transform: "",
    classList: "o_header_fixed,o_top_fixed_element",
};

const behavior2 = {
    visibility: true,
    paddingTop: "50px",
    transform: "translate(0px, 0px)",
    classList: "o_header_affixed,o_header_fixed,o_header_is_scrolled,o_top_fixed_element",
};

test("[scroll] Template without o_header_hide_on_scroll", async () => {
    const { core, el } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_fixed"));
    const wrapwrap = el.querySelector("#wrapwrap");
    const header = el.querySelector("header");
    const main = el.querySelector("main")
    await setupTest(core, wrapwrap);
    expect(checkHeader(header, main, core, behavior1)).toBe(true);
    await customScroll(wrapwrap, 0, 10);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 10, 400);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 400, 10);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 10, 0);
    expect(checkHeader(header, main, core, behavior1)).toBe(true);
});

test("[scroll] Template with o_header_hide_on_scroll", async () => {
    const { core, el } = await startInteractions(getTemplateWithHideOnScroll("o_header_fixed"));
    const wrapwrap = el.querySelector("#wrapwrap");
    const header = el.querySelector("header");
    const main = el.querySelector("main")
    await setupTest(core, wrapwrap);
    expect(checkHeader(header, main, core, behavior1)).toBe(true);
    await customScroll(wrapwrap, 0, 10);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 10, 400);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 400, 10);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 10, 0);
    expect(checkHeader(header, main, core, behavior1)).toBe(true);
});
