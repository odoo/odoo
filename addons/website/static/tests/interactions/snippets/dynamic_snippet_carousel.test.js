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

const testTemplate = /* xml */ `
    <div id="wrapwrap">
        <section data-snippet="s_dynamic_snippet_carousel" class="s_dynamic_snippet_carousel s_dynamic pt32 pb32 o_colored_level" data-custom-template-data="{}" data-name="Dynamic Carousel"
                data-filter-id="1"
                data-template-key="website.dynamic_filter_template_test_item"
                data-number-of-records="16"
                data-extra-classes="g-3"
                data-column-classes="col-12 col-sm-6 col-lg-4"
                data-carousel-interval="5000">
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
    </div>`;

test.tags("desktop");
test("dynamic snippet carousel loads items and displays them through template (desktop)", async () => {
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
    expect(itemEls[3].closest(".carousel-item")).toHaveClass("active");
    expect(itemEls[4].closest(".carousel-item")).not.toHaveClass("active");
    await animationFrame();
    await click(".carousel-control-next .oi");
    await animationFrame();
    await advanceTime(1000); // Slide duration.
    expect(itemEls[3].closest(".carousel-item")).not.toHaveClass("active");
    expect(itemEls[4].closest(".carousel-item")).toHaveClass("active");
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
