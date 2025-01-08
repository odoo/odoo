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

setupInteractionWhiteList("website.header_standard");

describe.current.tags("interaction_dev");

test("header_standard is started when there is an element header.o_header_standard", async () => {
    const { core } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_standard"));
    expect(core.interactions).toHaveLength(1);
});

const behaviorWithout = [{
    visibility: true,
    paddingTop: "",
    transform: "",
    classList: "o_header_standard,o_top_fixed_element",
}, {
    visibility: false,
    paddingTop: "50px",
    transform: "translate(0px, -100%)",
    classList: "o_header_affixed,o_header_standard",
}, {
    visibility: true,
    paddingTop: "50px",
    transform: "translate(0px, 0px)",
    classList: "o_header_affixed,o_header_is_scrolled,o_header_standard,o_top_fixed_element",
}];

test("[scroll] Template without o_header_hide_on_scroll", async () => {
    const { core, el } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_standard"));
    const wrapwrap = el.querySelector("#wrapwrap");
    const header = el.querySelector("header");
    const main = el.querySelector("main")
    await setupTest(core, wrapwrap);
    expect(checkHeader(header, main, core, behaviorWithout[0])).toBe(true);
    await customScroll(wrapwrap, 0, 40);
    expect(checkHeader(header, main, core, behaviorWithout[0])).toBe(true);
    await customScroll(wrapwrap, 40, 60);
    expect(checkHeader(header, main, core, behaviorWithout[1])).toBe(true);
    await customScroll(wrapwrap, 60, 290);
    expect(checkHeader(header, main, core, behaviorWithout[1])).toBe(true);
    await customScroll(wrapwrap, 290, 310);
    expect(checkHeader(header, main, core, behaviorWithout[2])).toBe(true);
    await customScroll(wrapwrap, 310, 400);
    expect(checkHeader(header, main, core, behaviorWithout[2])).toBe(true);
    await customScroll(wrapwrap, 400, 310);
    expect(checkHeader(header, main, core, behaviorWithout[2])).toBe(true);
    await customScroll(wrapwrap, 310, 290);
    expect(checkHeader(header, main, core, behaviorWithout[1])).toBe(true);
    await customScroll(wrapwrap, 290, 60);
    expect(checkHeader(header, main, core, behaviorWithout[1])).toBe(true);
    await customScroll(wrapwrap, 60, 40);
    expect(checkHeader(header, main, core, behaviorWithout[0])).toBe(true);
    await customScroll(wrapwrap, 40, 0);
    expect(checkHeader(header, main, core, behaviorWithout[0])).toBe(true);
});

const behaviorWithDesktop = [{
    visibility: true,
    paddingTop: "",
    transform: "",
    classList: "o_header_standard,o_top_fixed_element",
}, {
    visibility: false,
    paddingTop: "50px",
    transform: "translate(0px, -100%)",
    classList: "o_header_affixed,o_header_standard",
}, {
    visibility: true,
    paddingTop: "50px",
    transform: "translate(0px, 0px)",
    classList: "o_header_affixed,o_header_is_scrolled,o_header_standard,o_top_fixed_element",
}];

test.tags("desktop")("[scroll] Template with o_header_hide_on_scroll (desktop)", async () => {
    const { core, el } = await startInteractions(getTemplateWithHideOnScroll("o_header_standard"));
    const wrapwrap = el.querySelector("#wrapwrap");
    const header = el.querySelector("header");
    const main = el.querySelector("main")
    await setupTest(core, wrapwrap);
    expect(checkHeader(header, main, core, behaviorWithDesktop[0])).toBe(true);
    await customScroll(wrapwrap, 0, 40);
    expect(checkHeader(header, main, core, behaviorWithDesktop[0])).toBe(true);
    await customScroll(wrapwrap, 40, 60);
    expect(checkHeader(header, main, core, behaviorWithDesktop[1])).toBe(true);
    await customScroll(wrapwrap, 60, 290);
    expect(checkHeader(header, main, core, behaviorWithDesktop[1])).toBe(true);
    await customScroll(wrapwrap, 290, 310);
    expect(checkHeader(header, main, core, behaviorWithDesktop[2])).toBe(true);
    await customScroll(wrapwrap, 310, 400);
    expect(checkHeader(header, main, core, behaviorWithDesktop[2])).toBe(true);
    await customScroll(wrapwrap, 400, 310);
    expect(checkHeader(header, main, core, behaviorWithDesktop[2])).toBe(true);
    await customScroll(wrapwrap, 310, 290);
    expect(checkHeader(header, main, core, behaviorWithDesktop[1])).toBe(true);
    await customScroll(wrapwrap, 290, 60);
    expect(checkHeader(header, main, core, behaviorWithDesktop[1])).toBe(true);
    await customScroll(wrapwrap, 60, 40);
    expect(checkHeader(header, main, core, behaviorWithDesktop[0])).toBe(true);
    await customScroll(wrapwrap, 40, 0);
    expect(checkHeader(header, main, core, behaviorWithDesktop[0])).toBe(true);
});

const behaviorWithMobile = [{
    visibility: true,
    paddingTop: "",
    transform: "",
    classList: "o_header_standard,o_top_fixed_element",
}, {
    visibility: false,
    paddingTop: "30px",
    transform: "translate(0px, -100%)",
    classList: "o_header_affixed,o_header_standard",
}, {
    visibility: true,
    paddingTop: "30px",
    transform: "translate(0px, 0px)",
    classList: "o_header_affixed,o_header_is_scrolled,o_header_standard,o_top_fixed_element",
}];

test.tags("mobile")("[scroll] Template with o_header_hide_on_scroll (mobile)", async () => {
    const { core, el } = await startInteractions(getTemplateWithHideOnScroll("o_header_standard"));
    const wrapwrap = el.querySelector("#wrapwrap");
    const header = el.querySelector("header");
    const main = el.querySelector("main")
    await setupTest(core, wrapwrap);
    expect(checkHeader(header, main, core, behaviorWithMobile[0])).toBe(true);
    await customScroll(wrapwrap, 0, 20);
    expect(checkHeader(header, main, core, behaviorWithMobile[0])).toBe(true);
    await customScroll(wrapwrap, 20, 60);
    expect(checkHeader(header, main, core, behaviorWithMobile[1])).toBe(true);
    await customScroll(wrapwrap, 60, 290);
    expect(checkHeader(header, main, core, behaviorWithMobile[1])).toBe(true);
    await customScroll(wrapwrap, 290, 310);
    expect(checkHeader(header, main, core, behaviorWithMobile[2])).toBe(true);
    await customScroll(wrapwrap, 310, 400);
    expect(checkHeader(header, main, core, behaviorWithMobile[2])).toBe(true);
    await customScroll(wrapwrap, 400, 310);
    expect(checkHeader(header, main, core, behaviorWithMobile[2])).toBe(true);
    await customScroll(wrapwrap, 310, 290);
    expect(checkHeader(header, main, core, behaviorWithMobile[1])).toBe(true);
    await customScroll(wrapwrap, 290, 60);
    expect(checkHeader(header, main, core, behaviorWithMobile[1])).toBe(true);
    await customScroll(wrapwrap, 60, 20);
    expect(checkHeader(header, main, core, behaviorWithMobile[0])).toBe(true);
    await customScroll(wrapwrap, 20, 0);
    expect(checkHeader(header, main, core, behaviorWithMobile[0])).toBe(true);
});
