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

setupInteractionWhiteList("website.header_fixed");
beforeEach(enableTransitions);

describe.current.tags("interaction_dev");

test("header_fixed is started when there is an element header.o_header_fixed", async () => {
    const { core } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_fixed"));
    expect(core.interactions).toHaveLength(1);
});

const behaviorWithout = [
    {
        visibility: true,
        paddingTop: "0px",
        transform: "none",
        classList: "o_header_fixed o_top_fixed_element",
    },
    {
        visibility: true,
        paddingTop: "50px",
        transform: "matrix(1, 0, 0, 1, 0, 0)",
        classList: "o_header_affixed o_header_fixed o_header_is_scrolled o_top_fixed_element",
    },
];

test("[scroll] Template without o_header_hide_on_scroll", async () => {
    const { core } = await startInteractions(getTemplateWithoutHideOnScroll("o_header_fixed"));
    const wrapwrap = queryOne("#wrapwrap");
    const header = queryOne("header");
    const main = queryOne("main");
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

const behaviorWith = [
    {
        visibility: true,
        paddingTop: "0px",
        transform: "none",
        classList: "o_header_fixed o_top_fixed_element",
    },
    {
        visibility: true,
        paddingTop: "40px",
        transform: "matrix(1, 0, 0, 1, 0, 0)",
        classList: "o_header_affixed o_header_fixed o_header_is_scrolled o_top_fixed_element",
    },
    {
        visibility: true,
        paddingTop: "30px",
        transform: "matrix(1, 0, 0, 1, 0, 0)",
        classList: "o_header_affixed o_header_fixed o_header_is_scrolled o_top_fixed_element",
    },
];

test.tags("desktop");
test("[scroll] Template with o_header_hide_on_scroll", async () => {
    const { core } = await startInteractions(getTemplateWithHideOnScroll("o_header_fixed"));
    const wrapwrap = queryOne("#wrapwrap");
    const header = queryOne("header");
    const main = queryOne("main");
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
