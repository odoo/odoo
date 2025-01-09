import { describe, expect, test } from "@odoo/hoot";
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
registry.category("public.interactions").add("website_event.test_events_item", TestItem);
describe.current.tags("interaction_dev");

setupInteractionWhiteList(["website_event.events", "website_event.test_events_item"]);

test("dynamic snippet loads items and displays them through template", async () => {
    onRpc("/website/snippet/filters", async (args) => {
        const json = JSON.parse(new TextDecoder().decode(await args.arrayBuffer()));
        expect(json.params.filter_id).toBe(1);
        expect(json.params.template_key).toBe("website_event.dynamic_filter_template_event_event_picture");
        expect(json.params.limit).toBe(3);
        expect(json.params.search_domain).toEqual([["tag_ids", "in", [5]]]);
        return [`
            <div class="s_test_item" data-test-param="test">
                Some test record
            </div>
        `, `
            <div class="s_test_item" data-test-param="test2">
                Another test record
            </div>
        `];
    });
    const { core, el } = await startInteractions(`
      <div id="wrapwrap">
          <section data-snippet="s_events" class="s_events s_event_upcoming_snippet s_event_event_picture s_dynamic s_dynamic_empty pt32 pb32 o_colored_level"
                  data-custom-template-data="{&quot;events_event_time_active&quot;:true}"
                  data-name="Events"
                  data-filter-id="1"
                  data-filter-by-tag-ids="[{&quot;id&quot;:5,&quot;name&quot;:&quot;Culture&quot;,&quot;display_name&quot;:&quot;Culture&quot;,&quot;category_id&quot;:&quot;2,Activity&quot;}]"
                  data-template-key="website_event.dynamic_filter_template_event_event_picture"
                  data-number-of-records="3"
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
    expect(core.interactions.length).toBe(3);
    const contentEl = el.querySelector(".dynamic_snippet_template");
    const itemEls = contentEl.querySelectorAll(".s_test_item");
    expect(itemEls[0].dataset.testParam).toBe("test");
    expect(itemEls[1].dataset.testParam).toBe("test2");
    // Make sure element interactions are started.
    expect(itemEls[0].dataset.started).toBe("*test*");
    expect(itemEls[1].dataset.started).toBe("*test2*");
    core.stopInteractions();
    // Make sure element interactions are stopped.
    expect(core.interactions.length).toBe(0);
});
