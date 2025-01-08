import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

import { onRpc } from "@web/../tests/web_test_helpers";

import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

class TestDynamicCarouselItem extends Interaction {
    static selector = ".s_test_dynamic_carousel_item";
    dynamicContent = {
        "_root": {
            "t-att-data-started": (el) => `*${el.dataset.testParam}*`,
        },
    };
}
registry
    .category("public.interactions")
    .add("website.test_dynamic_carousel_item", TestDynamicCarouselItem);

setupInteractionWhiteList(["website.dynamic_snippet_carousel", "website.test_dynamic_carousel_item"]);

describe.current.tags("interaction_dev");

const testTemplate = `
    <div id="wrapwrap">
        <section data-snippet="s_dynamic_snippet_carousel" class="s_dynamic_snippet_carousel s_dynamic s_dynamic_empty pt32 pb32 o_colored_level" data-custom-template-data="{}" data-name="Dynamic Carousel"
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
    </div>`

test.tags("desktop")("dynamic snippet carousel loads items and displays them through template (desktop)", async () => {
    onRpc("/website/snippet/filters", async (args) => {
        for await (const chunk of args.body) {
            const json = JSON.parse(new TextDecoder().decode(chunk));
            expect(json.params.filter_id).toBe(1);
            expect(json.params.template_key).toBe("website.dynamic_filter_template_test_item");
            expect(json.params.limit).toBe(16);
            expect(json.params.search_domain).toEqual([]);
        }
        return [`<div class="s_test_dynamic_carousel_item" data-test-param="test1">Test Record 1</div>`,
            `<div class="s_test_dynamic_carousel_item" data-test-param="test2">Test Record 2</div>`,
            `<div class="s_test_dynamic_carousel_item" data-test-param="test3">Test Record 3</div>`,
            `<div class="s_test_dynamic_carousel_item" data-test-param="test4">Test Record 4</div>`,
            `<div class="s_test_dynamic_carousel_item" data-test-param="test5">Test Record 5</div>`,
        ];
    });
    const { core, el } = await startInteractions(testTemplate);
    expect(core.interactions).toHaveLength(6);
    const carouselEl = el.querySelector(".carousel");
    // Neutralize carousel automatic sliding.
    carouselEl.dataset.bsRide = "false";
    const itemEls = carouselEl.querySelectorAll(".s_test_dynamic_carousel_item");
    expect(itemEls[0].dataset.testParam).toBe("test1");
    expect(itemEls[1].dataset.testParam).toBe("test2");
    expect(itemEls[2].dataset.testParam).toBe("test3");
    expect(itemEls[3].dataset.testParam).toBe("test4");
    expect(itemEls[4].dataset.testParam).toBe("test5");
    expect(itemEls[3].closest(".carousel-item")).toHaveClass("active");
    expect(itemEls[4].closest(".carousel-item")).not.toHaveClass("active");
    await animationFrame();
    const nextEl = el.querySelector(".carousel-control-next .oi");
    await click(nextEl);
    await animationFrame();
    await advanceTime(1000); // Slide duration.
    expect(itemEls[3].closest(".carousel-item")).not.toHaveClass("active");
    expect(itemEls[4].closest(".carousel-item")).toHaveClass("active");
    // Make sure element interactions are started.
    expect(itemEls[0].dataset.started).toBe("*test1*");
    expect(itemEls[1].dataset.started).toBe("*test2*");
    expect(itemEls[2].dataset.started).toBe("*test3*");
    expect(itemEls[3].dataset.started).toBe("*test4*");
    expect(itemEls[4].dataset.started).toBe("*test5*");
    core.stopInteractions();
    // Make sure element interactions are stopped.
    expect(core.interactions).toHaveLength(0);
});

test.tags("mobile")("dynamic snippet carousel loads items and displays them through template (mobile)", async () => {
    onRpc("/website/snippet/filters", async (args) => {
        for await (const chunk of args.body) {
            const json = JSON.parse(new TextDecoder().decode(chunk));
            expect(json.params.filter_id).toBe(1);
            expect(json.params.template_key).toBe("website.dynamic_filter_template_test_item");
            expect(json.params.limit).toBe(16);
            expect(json.params.search_domain).toEqual([]);
        }
        return [`<div class="s_test_dynamic_carousel_item" data-test-param="test1">Test Record 1</div>`,
            `<div class="s_test_dynamic_carousel_item" data-test-param="test2">Test Record 2</div>`,
            `<div class="s_test_dynamic_carousel_item" data-test-param="test3">Test Record 3</div>`,
            `<div class="s_test_dynamic_carousel_item" data-test-param="test4">Test Record 4</div>`,
            `<div class="s_test_dynamic_carousel_item" data-test-param="test5">Test Record 5</div>`,
        ];
    });
    const { core, el } = await startInteractions(testTemplate);
    expect(core.interactions).toHaveLength(6);
    const carouselEl = el.querySelector(".carousel");
    // Neutralize carousel automatic sliding.
    carouselEl.dataset.bsRide = "false";
    const itemEls = carouselEl.querySelectorAll(".s_test_dynamic_carousel_item");
    expect(itemEls[0].dataset.testParam).toBe("test1");
    expect(itemEls[1].dataset.testParam).toBe("test2");
    expect(itemEls[2].dataset.testParam).toBe("test3");
    expect(itemEls[3].dataset.testParam).toBe("test4");
    expect(itemEls[4].dataset.testParam).toBe("test5");
    expect(itemEls[0].closest(".carousel-item")).toHaveClass("active");
    expect(itemEls[1].closest(".carousel-item")).not.toHaveClass("active");
    await animationFrame();
    const nextEl = el.querySelector(".carousel-control-next .oi");
    await click(nextEl);
    await animationFrame();
    await advanceTime(1000); // Slide duration.
    expect(itemEls[0].closest(".carousel-item")).not.toHaveClass("active");
    expect(itemEls[1].closest(".carousel-item")).toHaveClass("active");
    // Make sure element interactions are started.
    expect(itemEls[0].dataset.started).toBe("*test1*");
    expect(itemEls[1].dataset.started).toBe("*test2*");
    expect(itemEls[2].dataset.started).toBe("*test3*");
    expect(itemEls[3].dataset.started).toBe("*test4*");
    expect(itemEls[4].dataset.started).toBe("*test5*");
    core.stopInteractions();
    // Make sure element interactions are stopped.
    expect(core.interactions).toHaveLength(0);
});
