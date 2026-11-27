import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, queryAll, queryOne } from "@odoo/hoot-dom";
import { advanceTime, enableTransitions } from "@odoo/hoot-mock";

import { onRpc } from "@web/../tests/web_test_helpers";

import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

class TestDynamicCarouselItem extends Interaction {
    static selector = ".s_test_dynamic_carousel_item";
    dynamicContent = {
        _root: {
            "t-att-data-started": (el) => `*${el.dataset.testParam}*`,
        },
    };
}

setupInteractionWhiteList([
    "website.dynamic_snippet_carousel",
    "website.test_dynamic_carousel_item",
]);
beforeEach(() => {
    enableTransitions();

    registry
        .category("public.interactions")
        .add("website.test_dynamic_carousel_item", TestDynamicCarouselItem);
});

describe.current.tags("interaction_dev");

const singleScrollTemplate = /* xml */ `
    <div id="wrapwrap">
        <section data-snippet="s_dynamic_snippet_carousel" class="s_dynamic_snippet_carousel s_dynamic o_carousel_multi_items pt32 pb32 o_colored_level" data-custom-template-data="{}" data-name="Dynamic Carousel"
                data-filter-id="1"
                data-template-key="website.dynamic_filter_template_test_item"
                data-number-of-records="4"
                data-carousel-interval="1000">
            <div class="container">
                <div class="row s_nb_column_fixed">
                    <section class="s_dynamic_snippet_content oe_unremovable oe_unmovable o_not_editable col o_colored_level">
                        <div class="css_non_editable_mode_hidden">
                            <div class="missing_option_warning alert alert-info fade show d-none d-print-none rounded-0">
                            Your Dynamic Snippet will be displayed here... This message is displayed because you did not provide both a filter and a template to use.
                                <br/>
                            </div>
                        </div>
                        <div class="dynamic_snippet_template"></div>
                    </section>
                </div>
            </div>
        </section>
    </div>;
`;

test.tags("desktop");
test("dynamic carousel snippet doesn't slide when number of records is less than chunksize", async () => {
    onRpc("/website/snippet/filters", async () => [
        `<div class="s_test_dynamic_carousel_single_item">Test Record 1</div>`,
        `<div class="s_test_dynamic_carousel_single_item">Test Record 2</div>`,
        `<div class="s_test_dynamic_carousel_single_item">Test Record 3</div>`,
        `<div class="s_test_dynamic_carousel_single_item">Test Record 4</div>`,
    ]);
    await startInteractions(singleScrollTemplate);
    expect(".carousel").not.toHaveClass("o_carousel_multi_items");
    const carouselItemEls = queryAll(".carousel-item");
    expect(carouselItemEls).toHaveLength(1);
    expect(carouselItemEls[0]).toHaveClass("active");
    const itemEls = queryAll(".carousel .s_test_dynamic_carousel_single_item");
    expect(itemEls).toHaveLength(4);
    expect(queryAll(".carousel-control-prev")).toHaveLength(0);
    expect(queryAll(".carousel-control-next")).toHaveLength(0);
});

const testTemplate = /* xml */ `
    <div id="wrapwrap">
        <section data-snippet="s_dynamic_snippet_carousel" class="s_dynamic_snippet_carousel s_dynamic pt32 pb32 o_colored_level" data-custom-template-data="{}" data-name="Dynamic Carousel"
                data-filter-id="1"
                data-template-key="website.dynamic_filter_template_test_item"
                data-number-of-records="24"
                data-extra-classes="g-3"
                data-column-classes="col-12 col-sm-6 col-lg-4"
                data-carousel-interval="5000">
            <div class="container">
                <div class="row s_nb_column_fixed">
                    <section class="s_dynamic_content_holder d-none px-4 placeholder-glow">
                        <div class="row mt-4">
                            <span class="placeholder col-12 rounded" style="height:250px;"/>
                        </div>
                    </section>
                    <section class="s_dynamic_snippet_content oe_unremovable oe_unmovable o_not_editable col o_colored_level">
                        <div class="css_non_editable_mode_hidden">
                            <div class="missing_option_warning alert alert-info fade show d-none d-print-none rounded-0">
                            Your Dynamic Snippet will be displayed here... This message is displayed because you did not provide both a filter and a template to use.
                                <br/>
                            </div>
                        </div>
                        <div class="dynamic_snippet_template"></div>
                    </section>
                </div>
            </div>
        </section>
    </div>`;

test.tags("desktop");
test("dynamic snippet carousel loads items and displays them through template (desktop)", async () => {
    const rpcCalls = [];
    onRpc("/website/snippet/filters", async (args) => {
        const json = JSON.parse(new TextDecoder().decode(await args.arrayBuffer()));
        rpcCalls.push(json.params);
        const offset = json.params.offset || 0;
        if (offset === 0) {
            return [
                `<div class="s_test_dynamic_carousel_item" data-test-param="test1">Test Record 1</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test2">Test Record 2</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test3">Test Record 3</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test4">Test Record 4</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test5">Test Record 5</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test6">Test Record 6</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test7">Test Record 7</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test8">Test Record 8</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test9">Test Record 9</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test10">Test Record 10</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test11">Test Record 11</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test12">Test Record 12</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test13">Test Record 13</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test14">Test Record 14</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test15">Test Record 15</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test16">Test Record 16</div>`,
            ];
        } else if (offset === 16) {
            return [
                `<div class="s_test_dynamic_carousel_item" data-test-param="test17">Test Record 17</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test18">Test Record 18</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test19">Test Record 19</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test20">Test Record 20</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test21">Test Record 21</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test22">Test Record 22</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test23">Test Record 23</div>`,
                `<div class="s_test_dynamic_carousel_item" data-test-param="test24">Test Record 24</div>`,
            ];
        }
    });
    const { core } = await startInteractions(testTemplate);
    expect(rpcCalls[0]).toMatchObject({
        filter_id: 1,
        template_key: "website.dynamic_filter_template_test_item",
        limit: 16,
        offset: 0,
    });
    expect(core.interactions).toHaveLength(17);
    const carouselEl = queryOne(".carousel");
    // Neutralize carousel automatic sliding.
    carouselEl.dataset.bsRide = "false";
    let itemEls = queryAll(".carousel .s_test_dynamic_carousel_item");
    expect(queryAll(".carousel-item")).toHaveLength(4);
    expect(itemEls[0]).toHaveAttribute("data-test-param", "test1");
    expect(itemEls[15]).toHaveAttribute("data-test-param", "test16");
    expect(itemEls[3].closest(".carousel-item")).toHaveClass("active");
    expect(itemEls[4].closest(".carousel-item")).not.toHaveClass("active");
    await animationFrame();
    expect(".carousel-control-prev").toHaveClass("d-none");
    await click(".carousel-control-next .oi");
    await advanceTime(1000); // Slide duration.
    expect(".carousel-control-prev").not.toHaveClass("d-none");
    expect(itemEls[4].closest(".carousel-item")).toHaveClass("active");

    await click(".carousel-control-next .oi");
    await advanceTime(1000); // Slide duration.
    await click(".carousel-control-next .oi");
    await advanceTime(1000); // Slide duration.
    expect(itemEls[12].closest(".carousel-item")).toHaveClass("active");

    // Make sure element interactions are started.
    expect(itemEls[0]).toHaveAttribute("data-started", "*test1*");
    expect(itemEls[15]).toHaveAttribute("data-started", "*test16*");
    await click(".carousel-control-next .oi");
    expect(".s_dynamic_content_holder").not.toHaveClass("d-none");
    await animationFrame();
    expect(rpcCalls[1]).toMatchObject({
        filter_id: 1,
        template_key: "website.dynamic_filter_template_test_item",
        limit: 8,
        offset: 16,
    });
    expect(".s_dynamic_content_holder").toHaveClass("d-none");
    await advanceTime(1000); // Slide duration.
    itemEls = queryAll(".carousel .s_test_dynamic_carousel_item");
    expect(itemEls[15].closest(".carousel-item")).not.toHaveClass("active");
    expect(itemEls[16].closest(".carousel-item")).toHaveClass("active");
    expect(itemEls[16]).toHaveAttribute("data-started", "*test17*");
    expect(itemEls[19]).toHaveAttribute("data-started", "*test20*");
    expect(queryAll(".carousel-item")).toHaveLength(6);
    expect(core.interactions).toHaveLength(25);
    core.stopInteractions();
    // Make sure element interactions are stopped.
    expect(core.interactions).toHaveLength(0);
});

test.tags("mobile");
test("dynamic snippet carousel loads items and displays them through template (mobile)", async () => {
    onRpc("/website/snippet/filters", async (args) => {
        const json = JSON.parse(new TextDecoder().decode(await args.arrayBuffer()));
        expect(json.params.filter_id).toBe(1);
        expect(json.params.template_key).toBe("website.dynamic_filter_template_test_item");
        expect(json.params.limit).toBe(16);
        expect(json.params.search_domain).toEqual([]);
        return [
            `<div class="s_test_dynamic_carousel_item" data-test-param="test1">Test Record 1</div>`,
            `<div class="s_test_dynamic_carousel_item" data-test-param="test2">Test Record 2</div>`,
            `<div class="s_test_dynamic_carousel_item" data-test-param="test3">Test Record 3</div>`,
            `<div class="s_test_dynamic_carousel_item" data-test-param="test4">Test Record 4</div>`,
            `<div class="s_test_dynamic_carousel_item" data-test-param="test5">Test Record 5</div>`,
        ];
    });
    const { core } = await startInteractions(testTemplate);
    expect(core.interactions).toHaveLength(6);
    const carouselEl = queryOne(".carousel");
    // Neutralize carousel automatic sliding.
    carouselEl.dataset.bsRide = "false";
    const itemEls = queryAll(".carousel .s_test_dynamic_carousel_item");
    expect(itemEls[0]).toHaveAttribute("data-test-param", "test1");
    expect(itemEls[1]).toHaveAttribute("data-test-param", "test2");
    expect(itemEls[2]).toHaveAttribute("data-test-param", "test3");
    expect(itemEls[3]).toHaveAttribute("data-test-param", "test4");
    expect(itemEls[4]).toHaveAttribute("data-test-param", "test5");
    expect(itemEls[0].closest(".carousel-item")).toHaveClass("active");
    expect(itemEls[1].closest(".carousel-item")).not.toHaveClass("active");
    await animationFrame();
    await click(".carousel-control-next .oi");
    await animationFrame();
    await advanceTime(1000); // Slide duration.
    expect(itemEls[0].closest(".carousel-item")).not.toHaveClass("active");
    expect(itemEls[1].closest(".carousel-item")).toHaveClass("active");
    // Make sure element interactions are started.
    expect(itemEls[0]).toHaveAttribute("data-started", "*test1*");
    expect(itemEls[1]).toHaveAttribute("data-started", "*test2*");
    expect(itemEls[2]).toHaveAttribute("data-started", "*test3*");
    expect(itemEls[3]).toHaveAttribute("data-started", "*test4*");
    expect(itemEls[4]).toHaveAttribute("data-started", "*test5*");
    core.stopInteractions();
    // Make sure element interactions are stopped.
    expect(core.interactions).toHaveLength(0);
});
