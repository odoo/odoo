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

setupInteractionWhiteList("website.header_fixed");

describe.current.tags("interaction_dev");

test("header_fixed is started when there is an element header.o_header_fixed", async () => {
    const { core } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_fixed"));
    expect(core.interactions).toHaveLength(1);
});

const behaviorWithout = [{
    visibility: true,
    paddingTop: "0px",
    transform: "none",
    classList: "o_header_fixed o_top_fixed_element",
}, {
    visibility: true,
    paddingTop: "50px",
    transform: "matrix(1, 0, 0, 1, 0, 0)",
    classList: "o_header_affixed o_header_fixed o_header_is_scrolled o_top_fixed_element",
}];

test("[scroll] Template without o_header_hide_on_scroll", async () => {
    const { core, el } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_fixed"));
    const wrapwrap = el.querySelector("#wrapwrap");
    const header = el.querySelector("header");
    const main = el.querySelector("main");
    await setupTest(core, wrapwrap);
    checkHeader(header, main, core, behaviorWithout[0]);
    await customScroll(wrapwrap, 0, 10);
    checkHeader(header, main, core, behaviorWithout[1]);
    await customScroll(wrapwrap, 10, 400);
    checkHeader(header, main, core, behaviorWithout[1]);
    await customScroll(wrapwrap, 400, 10);
    checkHeader(header, main, core, behaviorWithout[1]);
    await customScroll(wrapwrap, 10, 0);
    checkHeader(header, main, core, behaviorWithout[0]);
});

const behaviorWith = [{
    visibility: true,
    paddingTop: "0px",
    transform: "none",
    classList: "o_header_fixed o_top_fixed_element",
}, {
    visibility: true,
    paddingTop: "50px",
    transform: "matrix(1, 0, 0, 1, 0, -10)",
    classList: "o_header_affixed o_header_fixed o_header_is_scrolled o_top_fixed_element",
}, {
    visibility: true,
    paddingTop: "50px",
    transform: "matrix(1, 0, 0, 1, 0, -20)",
    classList: "o_header_affixed o_header_fixed o_header_is_scrolled o_top_fixed_element",
}];

test("[scroll] Template with o_header_hide_on_scroll", async () => {
    const { core, el } = await startInteractions(getTemplateWithHideOnScroll("o_header_fixed"));
    const wrapwrap = el.querySelector("#wrapwrap");
    const header = el.querySelector("header");
    const main = el.querySelector("main");
    await setupTest(core, wrapwrap);
    checkHeader(header, main, core, behaviorWith[0]);
    await customScroll(wrapwrap, 0, 10);
    checkHeader(header, main, core, behaviorWith[1]);
    await customScroll(wrapwrap, 10, 400);
    checkHeader(header, main, core, behaviorWith[2]);
    await customScroll(wrapwrap, 400, 10);
    checkHeader(header, main, core, behaviorWith[1]);
    await customScroll(wrapwrap, 10, 0);
    checkHeader(header, main, core, behaviorWith[0]);
});
