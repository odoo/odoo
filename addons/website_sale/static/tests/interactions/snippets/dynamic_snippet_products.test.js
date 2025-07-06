import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, queryAll, queryOne } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { onRpc } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

class TestItem extends Interaction {
    static selector = ".s_test_item";
    dynamicContent = {
        _root: {
            "t-att-data-started": (el) => `*${el.dataset.testParam}*`,
        },
    };
}

setupInteractionWhiteList([
    "website_sale.dynamic_snippet_products",
    "website_sale.test_dynamic_carousel_products_item",
]);
beforeEach(() => {
    registry
        .category("public.interactions")
        .add("website_sale.test_dynamic_carousel_products_item", TestItem);
});

describe.current.tags("interaction_dev");

test.tags("desktop");
test("dynamic snippet products loads items and displays them through template", async () => {
    document.documentElement.dataset.mainObject = "product.public.category(2,)";
    onRpc("/website/snippet/filters", async (args) => {
        const json = JSON.parse(new TextDecoder().decode(await args.arrayBuffer()));
        expect(json.params.filter_id).toBe(3);
        expect(json.params.template_key).toBe(
            "website_sale.dynamic_filter_template_product_product_products_item"
        );
        expect(json.params.limit).toBe(16);
        expect(json.params.search_domain).toEqual([["public_categ_ids", "child_of", 2]]);
        return [
            `
            <div class="s_test_item" data-test-param="test">
                Some test record
            </div>
        `,
            `
            <div class="s_test_item" data-test-param="test2">
                Another test record
            </div>
        `,
            `
            <div class="s_test_item" data-test-param="test3">
                Yet another test record
            </div>
        `,
            `
            <div class="s_test_item" data-test-param="test4">
                Last test record of first page
            </div>
        `,
            `
            <div class="s_test_item" data-test-param="test5">
                Test record in second page
            </div>
        `,
        ];
    });
    const { core } = await startInteractions(`
      <div id="wrapwrap">
          <section data-snippet="s_dynamic_snippet_products" class="s_dynamic_snippet_products s_dynamic s_dynamic_empty pt32 pb32 o_colored_level s_product_product_borderless_1"
                  data-name="Products"
                  data-filter-id="3"
                  data-product-category-id="current"
                  data-show-variants="true"
                  data-custom-template-data="{}"
                  data-number-of-records="16"
                  data-template-key="website_sale.dynamic_filter_template_product_product_products_item"
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
    expect(core.interactions).toHaveLength(6);
    // Neutralize carousel automatic sliding.
    queryOne(".dynamic_snippet_template .carousel").dataset.bsRide = "false";
    const itemEls = queryAll(".s_test_item");
    expect(itemEls[0]).toHaveAttribute("data-test-param", "test");
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
    expect(itemEls[0]).toHaveAttribute("data-started", "*test*");
    expect(itemEls[1]).toHaveAttribute("data-started", "*test2*");
    expect(itemEls[2]).toHaveAttribute("data-started", "*test3*");
    expect(itemEls[3]).toHaveAttribute("data-started", "*test4*");
    expect(itemEls[4]).toHaveAttribute("data-started", "*test5*");
    core.stopInteractions();
    // Make sure element interactions are stopped.
    expect(core.interactions).toHaveLength(0);
});
