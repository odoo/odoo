import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";

import {
    setupTest,
    checkHeader,
    customScroll,
    getTemplateWithoutHideOnScroll,
    getTemplateWithHideOnScroll,
} from "./helpers";

setupInteractionWhiteList("website.header_fade_out");

describe.current.tags("interaction_dev");

test("header_fade_out is started when there is an element header.o_header_fade_out", async () => {
    const { core } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_fade_out"));
    expect(core.interactions).toHaveLength(1);
});

const behaviorWithout = [{
    visibility: true,
    paddingTop: "",
    transform: "",
    classList: "o_header_fade_out,o_top_fixed_element",
}, {
    visibility: true,
    paddingTop: "50px",
    transform: "translate(0px, 0px)",
    classList: "o_header_affixed,o_header_fade_out,o_header_is_scrolled,o_top_fixed_element",
}, {
    visibility: false,
    paddingTop: "50px",
    transform: "translate(0px, -100%)",
    classList: "o_header_affixed,o_header_fade_out,o_header_is_scrolled",
}];

test("[scroll] Template without o_header_hide_on_scroll", async () => {
    const { core, el } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_fade_out"));
    const wrapwrap = el.querySelector("#wrapwrap");
    const header = el.querySelector("header");
    const main = el.querySelector("main")
    await setupTest(core, wrapwrap);
    expect(checkHeader(header, main, core, behaviorWithout[0])).toBe(true);
    await customScroll(wrapwrap, 0, 10);
    expect(checkHeader(header, main, core, behaviorWithout[1])).toBe(true);
    await customScroll(wrapwrap, 10, 60);
    expect(checkHeader(header, main, core, behaviorWithout[1])).toBe(true);
    await customScroll(wrapwrap, 60, 190);
    expect(checkHeader(header, main, core, behaviorWithout[1])).toBe(true);
    await customScroll(wrapwrap, 190, 210);
    expect(checkHeader(header, main, core, behaviorWithout[2])).toBe(true);
    await customScroll(wrapwrap, 210, 400);
    expect(checkHeader(header, main, core, behaviorWithout[2])).toBe(true);
    await customScroll(wrapwrap, 400, 310);
    expect(checkHeader(header, main, core, behaviorWithout[2])).toBe(true);
    await customScroll(wrapwrap, 310, 290);
    expect(checkHeader(header, main, core, behaviorWithout[1])).toBe(true);
    await customScroll(wrapwrap, 290, 0);
    expect(checkHeader(header, main, core, behaviorWithout[0])).toBe(true);
});

const behaviorWith = [{
    visibility: true,
    paddingTop: "",
    transform: "",
    classList: "o_header_fade_out,o_top_fixed_element",
}, {
    visibility: true,
    paddingTop: "50px",
    transform: "translate(0px, -10px)",
    classList: "o_header_affixed,o_header_fade_out,o_header_is_scrolled,o_top_fixed_element",
}, {
    visibility: true,
    paddingTop: "50px",
    transform: "translate(0px, -20px)",
    classList: "o_header_affixed,o_header_fade_out,o_header_is_scrolled,o_top_fixed_element",
}, {
    visibility: false,
    paddingTop: "50px",
    transform: "translate(0px, -100%)",
    classList: "o_header_affixed,o_header_fade_out,o_header_is_scrolled",
}];

test("[scroll] Template with o_header_hide_on_scroll", async () => {
    const { core, el } = await startInteractions(getTemplateWithHideOnScroll("o_header_fade_out"));
    const wrapwrap = el.querySelector("#wrapwrap");
    const header = el.querySelector("header");
    const main = el.querySelector("main")
    await setupTest(core, wrapwrap);
    expect(checkHeader(header, main, core, behaviorWith[0])).toBe(true);
    await customScroll(wrapwrap, 0, 10);
    expect(checkHeader(header, main, core, behaviorWith[1])).toBe(true);
    await customScroll(wrapwrap, 10, 60);
    expect(checkHeader(header, main, core, behaviorWith[2])).toBe(true);
    await customScroll(wrapwrap, 60, 190);
    expect(checkHeader(header, main, core, behaviorWith[2])).toBe(true);
    await customScroll(wrapwrap, 190, 210);
    expect(checkHeader(header, main, core, behaviorWith[3])).toBe(true);
    await customScroll(wrapwrap, 210, 400);
    expect(checkHeader(header, main, core, behaviorWith[3])).toBe(true);
    await customScroll(wrapwrap, 400, 310);
    expect(checkHeader(header, main, core, behaviorWith[3])).toBe(true);
    await customScroll(wrapwrap, 310, 290);
    expect(checkHeader(header, main, core, behaviorWith[2])).toBe(true);
    await customScroll(wrapwrap, 290, 10);
    expect(checkHeader(header, main, core, behaviorWith[1])).toBe(true);
    await customScroll(wrapwrap, 10, 0);
    expect(checkHeader(header, main, core, behaviorWith[0])).toBe(true);
});
