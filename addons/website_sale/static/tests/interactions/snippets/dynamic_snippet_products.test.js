import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import {
    onRpc,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

class TestItem extends Interaction {
    static selector = ".s_test_item";
    dynamicContent = {
        "_root": {
            "t-att-data-started": (el) => `*${el.dataset.testParam}*`,
        },
    };
}
registry.category("public.interactions").add("website_sale.test_dynamic_carousel_products_item", TestItem);

setupInteractionWhiteList(["website_sale.dynamic_snippet_products", "website_sale.test_dynamic_carousel_products_item"]);
describe.current.tags("interaction_dev");

test.tags("desktop")("dynamic snippet products loads items and displays them through template", async () => {
    document.querySelector("html").dataset.mainObject = "product.public.category(2,)";
    onRpc("/website/snippet/filters", async (args) => {
        for await (const chunk of args.body) {
            const json = JSON.parse(new TextDecoder().decode(chunk));
            expect(json.params.filter_id).toBe(3);
            expect(json.params.template_key).toBe("website_sale.dynamic_filter_template_product_product_borderless_1");
            expect(json.params.limit).toBe(16);
            expect(json.params.search_domain).toEqual([[
                "public_categ_ids",
                "child_of",
                2,
            ]]);
        }
        return [`
            <div class="s_test_item" data-test-param="test">
                Some test record
            </div>
        `, `
            <div class="s_test_item" data-test-param="test2">
                Another test record
            </div>
        `, `
            <div class="s_test_item" data-test-param="test3">
                Yet another test record
            </div>
        `, `
            <div class="s_test_item" data-test-param="test4">
                Last test record of first page
            </div>
        `, `
            <div class="s_test_item" data-test-param="test5">
                Test record in second page
            </div>
        `];
    });
    const { core, el } = await startInteractions(`
      <div id="wrapwrap">
          <section data-snippet="s_dynamic_snippet_products" class="s_dynamic_snippet_products s_dynamic s_dynamic_empty pt32 pb32 o_colored_level s_product_product_borderless_1"
                  data-name="Products"
                  data-filter-id="3"
                  data-product-category-id="current"
                  data-show-variants="true"
                  data-custom-template-data="{}"
                  data-number-of-records="16"
                  data-template-key="website_sale.dynamic_filter_template_product_product_borderless_1"
                  data-carousel-interval="5000"
          >
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
      </div>
    `);
    expect(core.interactions.length).toBe(6);
    const contentEl = el.querySelector(".dynamic_snippet_template");
    const carouselEl = contentEl.querySelector(".carousel");
    // Neutralize carousel automatic sliding.
    carouselEl.dataset.bsRide = "false";
    const itemEls = carouselEl.querySelectorAll(".s_test_item");
    expect(itemEls[0].dataset.testParam).toBe("test");
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
    expect(itemEls[0].dataset.started).toBe("*test*");
    expect(itemEls[1].dataset.started).toBe("*test2*");
    expect(itemEls[2].dataset.started).toBe("*test3*");
    expect(itemEls[3].dataset.started).toBe("*test4*");
    expect(itemEls[4].dataset.started).toBe("*test5*");
    core.stopInteractions();
    // Make sure element interactions are stopped.
    expect(core.interactions.length).toBe(0);
});
