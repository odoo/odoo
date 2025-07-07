import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, queryAll } from "@odoo/hoot-dom";

import { onRpc } from "@web/../tests/web_test_helpers";

import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

class TestDynamicItem extends Interaction {
    static selector = ".s_test_dynamic_item";
    dynamicContent = {
        _root: { "t-att-data-started": (el) => `*${el.dataset.testParam}*` },
    };
}

beforeEach(() => {
    registry.category("public.interactions").add("website.test_dynamic_item", TestDynamicItem);
});

setupInteractionWhiteList(["website.dynamic_snippet", "website.test_dynamic_item"]);

describe.current.tags("interaction_dev");

test("dynamic snippet loads items and displays them through template", async () => {
    const rpcCalls = [];
    onRpc("/website/snippet/filters", async (args) => {
        const json = JSON.parse(new TextDecoder().decode(await args.arrayBuffer()));
        rpcCalls.push(json.params);
        const offset = json.params.offset || 0;
        if (offset === 0) {
            return [
                `<div class="s_test_dynamic_item" data-test-param="test1">Test Record 1</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test2">Test Record 2</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test3">Test Record 3</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test4">Test Record 4</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test5">Test Record 5</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test6">Test Record 6</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test7">Test Record 7</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test8">Test Record 8</div>`,
            ];
        } else if (offset === 8) {
            return [
                `<div class="s_test_dynamic_item" data-test-param="test9">Test Record 9</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test10">Test Record 10</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test11">Test Record 11</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test12">Test Record 12</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test13">Test Record 13</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test14">Test Record 14</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test15">Test Record 15</div>`,
                `<div class="s_test_dynamic_item" data-test-param="test16">Test Record 16</div>`,
            ];
        }
    });
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <section data-snippet="s_dynamic_snippet" class="s_dynamic_snippet s_dynamic pt32 pb32 o_colored_level" data-custom-template-data="{}" data-name="Dynamic Snippet"
                    data-filter-id="1"
                    data-template-key="website.dynamic_filter_template_test_item"
                    data-number-of-records="16"
                    data-extra-classes="g-3"
                    data-column-classes="col-12 col-sm-6 col-lg-4">
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
                        <section class="s_dynamic_snippet_load_more d-none">
                            <a href="www.odoo.com" class="btn">Load More</a>
                        </section>
                    </div>
                </div>
            </section>
        </div>
    `);
    expect(rpcCalls[0]).toMatchObject({
        filter_id: 1,
        template_key: "website.dynamic_filter_template_test_item",
        limit: 8,
        offset: 0,
        search_domain: [],
    });
    expect(core.interactions).toHaveLength(9);
    let itemEls = queryAll(".dynamic_snippet_template .s_test_dynamic_item");
    expect(itemEls[0]).toHaveAttribute("data-test-param", "test1");
    expect(itemEls[7]).toHaveAttribute("data-test-param", "test8");
    // Make sure element interactions are started.
    expect(itemEls[0]).toHaveAttribute("data-started", "*test1*");
    expect(itemEls[7]).toHaveAttribute("data-started", "*test8*");
    await click(".s_dynamic_snippet_load_more a");
    expect(rpcCalls[1]).toMatchObject({
        filter_id: 1,
        template_key: "website.dynamic_filter_template_test_item",
        limit: 8,
        offset: 8,
    });
    await animationFrame();
    itemEls = queryAll(".dynamic_snippet_template .s_test_dynamic_item");
    expect(itemEls[8]).toHaveAttribute("data-test-param", "test9");
    expect(itemEls[15]).toHaveAttribute("data-test-param", "test16");
    expect(itemEls[8]).toHaveAttribute("data-started", "*test9*");
    expect(itemEls[15]).toHaveAttribute("data-started", "*test16*");
    expect(core.interactions).toHaveLength(17);
    expect(".s_dynamic_snippet_load_more").not.toBeVisible();
    core.stopInteractions();
    // Make sure element interactions are stopped.
    expect(core.interactions).toHaveLength(0);
});
