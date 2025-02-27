import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { enableTransitions } from "@odoo/hoot-mock";

import {
    checkHeader,
    customScroll,
    getTemplateWithHideOnScroll,
    getTemplateWithoutHideOnScroll,
    setupTest,
} from "./helpers";

setupInteractionWhiteList("website.header_disappears");
beforeEach(enableTransitions);

describe.current.tags("interaction_dev");

test("header_disappears is started when there is an element header.o_header_disappears", async () => {
    const { core } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_disappears"));
    expect(core.interactions).toHaveLength(1);
});

const behaviorWithout = [
    {
        visibility: true,
        paddingTop: "0px",
        transform: "none",
        classList: "o_header_disappears o_top_fixed_element",
    },
    {
        visibility: true,
        paddingTop: "50px",
        transform: "matrix(1, 0, 0, 1, 0, 0)",
        classList: "o_header_affixed o_header_disappears o_header_is_scrolled o_top_fixed_element",
    },
    {
        visibility: false,
        paddingTop: "50px",
        transform: "matrix(1, 0, 0, 1, 0, -50)",
        classList: "o_header_affixed o_header_disappears o_header_is_scrolled",
    },
];

test("[scroll] Template without o_header_hide_on_scroll", async () => {
    const { core } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_disappears"));
    const wrapwrap = queryOne("#wrapwrap");
    const header = queryOne("header");
    const main = queryOne("main");
    await setupTest(core, wrapwrap);
    checkHeader(header, main, core, behaviorWithout[0]);
    await customScroll(wrapwrap, 0, 10);
    checkHeader(header, main, core, behaviorWithout[1]);
    await customScroll(wrapwrap, 10, 60);
    checkHeader(header, main, core, behaviorWithout[1]);
    await customScroll(wrapwrap, 60, 190);
    checkHeader(header, main, core, behaviorWithout[1]);
    await customScroll(wrapwrap, 190, 210);
    checkHeader(header, main, core, behaviorWithout[2]);
    await customScroll(wrapwrap, 210, 400);
    checkHeader(header, main, core, behaviorWithout[2]);
    await customScroll(wrapwrap, 400, 310);
    checkHeader(header, main, core, behaviorWithout[2]);
    await customScroll(wrapwrap, 310, 290);
    checkHeader(header, main, core, behaviorWithout[1]);
    await customScroll(wrapwrap, 290, 0);
    checkHeader(header, main, core, behaviorWithout[0]);
});

const behaviorWith = [
    {
        visibility: true,
        paddingTop: "0px",
        transform: "none",
        classList: "o_header_disappears o_top_fixed_element",
    },
    {
        visibility: true,
        paddingTop: "40px",
        transform: "matrix(1, 0, 0, 1, 0, 0)",
        classList: "o_header_affixed o_header_disappears o_header_is_scrolled o_top_fixed_element",
    },
    {
        visibility: true,
        paddingTop: "30px",
        transform: "matrix(1, 0, 0, 1, 0, 0)",
        classList: "o_header_affixed o_header_disappears o_header_is_scrolled o_top_fixed_element",
    },
    {
        visibility: false,
        paddingTop: "30px",
        transform: "matrix(1, 0, 0, 1, 0, -30)",
        classList: "o_header_affixed o_header_disappears o_header_is_scrolled",
    },
];

test.tags("desktop");
test("[scroll] Template with o_header_hide_on_scroll", async () => {
    const { core } = await startInteractions(getTemplateWithHideOnScroll("o_header_disappears"));
    const wrapwrap = queryOne("#wrapwrap");
    const header = queryOne("header");
    const main = queryOne("main");
    await setupTest(core, wrapwrap);
    checkHeader(header, main, core, behaviorWith[0]);
    await customScroll(wrapwrap, 0, 10);
    checkHeader(header, main, core, behaviorWith[1]);
    await customScroll(wrapwrap, 10, 60);
    checkHeader(header, main, core, behaviorWith[2]);
    await customScroll(wrapwrap, 60, 190);
    checkHeader(header, main, core, behaviorWith[2]);
    await customScroll(wrapwrap, 190, 210);
    checkHeader(header, main, core, behaviorWith[3]);
    await customScroll(wrapwrap, 210, 400);
    checkHeader(header, main, core, behaviorWith[3]);
    await customScroll(wrapwrap, 400, 310);
    checkHeader(header, main, core, behaviorWith[3]);
    await customScroll(wrapwrap, 310, 290);
    checkHeader(header, main, core, behaviorWith[2]);
    await customScroll(wrapwrap, 290, 10);
    checkHeader(header, main, core, behaviorWith[1]);
    await customScroll(wrapwrap, 10, 0);
    checkHeader(header, main, core, behaviorWith[0]);
});
