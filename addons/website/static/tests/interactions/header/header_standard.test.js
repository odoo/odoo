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

setupInteractionWhiteList("website.header_standard");

test("header_standard is started when there is an element header.o_header_standard", async () => {
    const { core } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_standard"));
    expect(core.interactions.length).toBe(1);
});

const behavior1 = {
    visibility: true,
    paddingTop: "",
    transform: "",
    classList: "o_header_standard,o_top_fixed_element",
};

const behavior2 = {
    visibility: false,
    paddingTop: "50px",
    transform: "translate(0px, -100%)",
    classList: "o_header_affixed,o_header_standard",
};

const behavior3 = {
    visibility: true,
    paddingTop: "50px",
    transform: "translate(0px, 0px)",
    classList: "o_header_affixed,o_header_is_scrolled,o_header_standard,o_top_fixed_element",
};

test("[scroll] Template without o_header_hide_on_scroll", async () => {
    const { core, el } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_standard"));
    const wrapwrap = el.querySelector("#wrapwrap");
    const header = el.querySelector("header");
    const main = el.querySelector("main")
    await setupTest(core, wrapwrap);
    expect(checkHeader(header, main, core, behavior1)).toBe(true);
    await customScroll(wrapwrap, 0, 40);
    expect(checkHeader(header, main, core, behavior1)).toBe(true);
    await customScroll(wrapwrap, 40, 60);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 60, 290);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 290, 310);
    expect(checkHeader(header, main, core, behavior3)).toBe(true);
    await customScroll(wrapwrap, 310, 400);
    expect(checkHeader(header, main, core, behavior3)).toBe(true);
    await customScroll(wrapwrap, 400, 310);
    expect(checkHeader(header, main, core, behavior3)).toBe(true);
    await customScroll(wrapwrap, 310, 290);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 290, 60);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 60, 40);
    expect(checkHeader(header, main, core, behavior1)).toBe(true);
    await customScroll(wrapwrap, 40, 0);
    expect(checkHeader(header, main, core, behavior1)).toBe(true);
});

test("[scroll] Template with o_header_hide_on_scroll", async () => {
    const { core, el } = await startInteractions(getTemplateWithHideOnScroll("o_header_standard"));
    const wrapwrap = el.querySelector("#wrapwrap");
    const header = el.querySelector("header");
    const main = el.querySelector("main")
    await setupTest(core, wrapwrap);
    expect(checkHeader(header, main, core, behavior1)).toBe(true);
    await customScroll(wrapwrap, 0, 40);
    expect(checkHeader(header, main, core, behavior1)).toBe(true);
    await customScroll(wrapwrap, 40, 60);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 60, 290);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 290, 310);
    expect(checkHeader(header, main, core, behavior3)).toBe(true);
    await customScroll(wrapwrap, 310, 400);
    expect(checkHeader(header, main, core, behavior3)).toBe(true);
    await customScroll(wrapwrap, 400, 310);
    expect(checkHeader(header, main, core, behavior3)).toBe(true);
    await customScroll(wrapwrap, 310, 290);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 290, 60);
    expect(checkHeader(header, main, core, behavior2)).toBe(true);
    await customScroll(wrapwrap, 60, 40);
    expect(checkHeader(header, main, core, behavior1)).toBe(true);
    await customScroll(wrapwrap, 40, 0);
    expect(checkHeader(header, main, core, behavior1)).toBe(true);
});
