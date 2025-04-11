import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
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

setupInteractionWhiteList(["website_blog.blog_posts", "website_blog.test_blog_post_item"]);
beforeEach(() => {
    registry.category("public.interactions").add("website_blog.test_blog_post_item", TestItem);
});

describe.current.tags("interaction_dev");

test("dynamic snippet blog posts loads items and displays them through template", async () => {
    onRpc("/website/snippet/filters", async (args) => {
        const json = JSON.parse(new TextDecoder().decode(await args.arrayBuffer()));
        expect(json.params.filter_id).toBe(1);
        expect(json.params.template_key).toBe(
            "website_blog.dynamic_filter_template_blog_post_big_picture"
        );
        expect(json.params.limit).toBe(16);
        expect(json.params.search_domain).toEqual([["blog_id", "=", 1]]);
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
        ];
    });
    const { core } = await startInteractions(`
      <div id="wrapwrap">
          <section data-snippet="s_blog_posts" class="s_blog_posts s_dynamic_snippet_blog_posts s_blog_post_big_picture s_blog_posts_effect_marley s_blog_posts_post_picture_size_default s_dynamic pt32 pb32 o_colored_level"
                  data-custom-template-data="{&quot;blog_posts_post_author_active&quot;:true, &quot;blog_posts_post_teaser_active&quot;:true, &quot;blog_posts_post_date_active&quot;:true}"
                  data-name="Blog Posts"
                  data-filter-by-blog-id="1"
                  data-filter-id="1"
                  data-template-key="website_blog.dynamic_filter_template_blog_post_big_picture"
                  data-number-of-records="16"
                  data-extra-classes="g-3"
                  data-column-classes="col-12 col-sm-6 col-lg-4"
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
    expect(core.interactions).toHaveLength(3);
    const itemEls = queryAll(".dynamic_snippet_template .s_test_item");
    expect(itemEls[0]).toHaveAttribute("data-test-param", "test");
    expect(itemEls[1]).toHaveAttribute("data-test-param", "test2");
    // Make sure element interactions are started.
    expect(itemEls[0]).toHaveAttribute("data-started", "*test*");
    expect(itemEls[1]).toHaveAttribute("data-started", "*test2*");
    core.stopInteractions();
    // Make sure element interactions are stopped.
    expect(core.interactions).toHaveLength(0);
});
