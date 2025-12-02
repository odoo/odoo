import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { click, microTick, queryOne } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";

import { onRpc } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList("website.listing_layout");

describe.current.tags("interaction_dev");

test("listing_layout toggle to list mode", async () => {
    const deferred = new Deferred();
    await startInteractions(`
        <div class="container o_website_listing_layout">
            <section>
                <div class="listing_layout_switcher btn-group" data-active-classes="border-primary" data-view-id="123">
                    <input id="apply_grid" type="radio" class="btn-check" value="grid" checked="checked">
                    <label title="Grid" for="apply_grid" class="btn">
                        <i class="fa fa-th-large"></i>
                    </label>
                    <input id="apply_list" type="radio" class="btn-check" value="list">
                    <label title="List" for="apply_list" class="btn">
                        <i class="oi oi-view-list"></i>
                    </label>
                </div>
            </section>
            <div class="o_website_grid">
                <div class="col-lg-3 col-md-4 col-sm-6 px-2 col-xs-12">
                    <a class="o_website_record text-decoration-none d-grid card w-100 mb-3" href="#">
                        Some data
                    </a>
                </div>
            </div>
        </div>
    `);
    onRpc("/website/save_session_layout_mode", async (request) => {
        const jsonParams = JSON.parse(
            new TextDecoder("utf-8").decode(await request.arrayBuffer())
        ).params;
        expect.step("rpc");
        expect(jsonParams.layout_mode).toBe("list");
        expect(jsonParams.view_id).toBe("123");
        deferred.resolve();
    });
    const gridEl = queryOne(".o_website_grid");
    await click("label[for=apply_list]");
    await microTick();
    expect(gridEl).toHaveClass("o_website_list");
    expect(gridEl).not.toHaveClass("o_website_grid");
    expect(queryOne(".o_website_list > div")).not.toHaveClass([
        "col-lg-3",
        "col-md-4",
        "col-sm-6",
        "px-2",
        "col-xs-12",
    ]);
    await deferred;
    expect.verifySteps(["rpc"]);
});

test("listing_layout toggle to grid mode", async () => {
    const deferred = new Deferred();
    await startInteractions(`
        <div class="container o_website_listing_layout">
            <section>
                <div class="listing_layout_switcher btn-group" data-active-classes="border-primary" data-view-id="123">
                    <input id="apply_grid" type="radio" class="btn-check" value="grid">
                    <label title="Grid" for="apply_grid" class="btn">
                        <i class="fa fa-th-large"></i>
                    </label>
                    <input id="apply_list" type="radio" class="btn-check" value="list" checked="checked">
                    <label title="List" for="apply_list" class="btn">
                        <i class="oi oi-view-list"></i>
                    </label>
                </div>
            </section>
            <div class="o_website_list">
                <div>
                    <a class="o_website_record text-decoration-none d-grid card w-100 mb-3" href="#">
                        Some data
                    </a>
                </div>
            </div>
        </div>
    `);
    onRpc("/website/save_session_layout_mode", async (request) => {
        const jsonParams = JSON.parse(
            new TextDecoder("utf-8").decode(await request.arrayBuffer())
        ).params;
        expect.step("rpc");
        expect(jsonParams.layout_mode).toBe("grid");
        expect(jsonParams.view_id).toBe("123");
        deferred.resolve();
    });
    const listEl = queryOne(".o_website_list");
    await click("label[for=apply_grid]");
    await microTick();
    expect(listEl).toHaveClass("o_website_grid");
    expect(listEl).not.toHaveClass("o_website_list");
    expect(queryOne(".o_website_grid > div")).toHaveClass([
        "col-lg-3",
        "col-md-4",
        "col-sm-6",
        "px-2",
        "col-xs-12",
    ]);
    await deferred;
    expect.verifySteps(["rpc"]);
});
