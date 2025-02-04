import { describe, expect, test } from "@odoo/hoot";
import {
    defineActions,
    defineModels,
    getService,
    makeMockEnv,
    models,
    onRpc,
} from "@web/../tests/web_test_helpers";

describe.current.tags("headless");

class TakeFive extends models.Model {
    _name = "take.five";
    _views = {
        "list,99": /* xml */ `<list><field name="display_name" /></list>`,
    };
}

class IrUiView extends models.Model {
    _name = "ir.ui.view";
}

defineModels([TakeFive, IrUiView]);

test("evaluate actionmenus", async () => {
    defineActions([
        {
            id: 1,
            name: "Fist Action",
            res_model: "take.five",
            search_view_id: [false, "search"],
            views: [[99, "list"]],
            binding_model_id: "take.five",
            binding_view_types: "list",
        },
        {
            id: 2, // not binded action
            name: "Second Action",
            res_model: "take.five",
            search_view_id: [false, "search"],
            views: [[99, "list"]],
        },
        {
            id: 3,
            name: "Third Action",
            res_model: "take.five",
            views: [[99, "list"]],
            binding_model_id: "anoter.model",
            binding_view_types: "list",
        },
        {
            id: 4,
            name: "Fist Invisible Action",
            res_model: "take.five",
            search_view_id: [false, "search"],
            views: [[99, "list"]],
            binding_model_id: "take.five",
            binding_view_types: "list",
            binding_invisible: true,
        },
        {
            id: 5,
            name: "Invisible with context",
            res_model: "take.five",
            search_view_id: [false, "search"],
            views: [[99, "list"]],
            binding_model_id: "take.five",
            binding_view_types: "list",
            binding_invisible: "companies.active_id == 1",
        },
        {
            id: 6,
            name: "Visible with context",
            res_model: "take.five",
            search_view_id: [false, "search"],
            views: [[99, "list"]],
            binding_model_id: "take.five",
            binding_view_types: "list",
            binding_invisible: "companies.active_id == 2",
        },
    ]);
    await makeMockEnv();
    const res = await getService("view").loadViews(
        {
            resModel: "take.five",
            views: [[99, "list"]],
        },
        { loadActionMenus: true }
    );
    expect(res.views.list.actionMenus.action).toEqual([
        {
            binding_view_types: "list",
            id: 1,
            name: "Fist Action",
        },
        {
            binding_invisible: "companies.active_id == 2",
            binding_view_types: "list",
            id: 6,
            name: "Visible with context",
        },
    ]);
});
test("stores calls in cache in success", async () => {
    expect.assertions(1);
    onRpc("get_views", () => {
        expect.step("get_views");
    });
    await makeMockEnv();
    await getService("view").loadViews(
        {
            resModel: "take.five",
            views: [[99, "list"]],
            context: { default_field_value: 1 },
        },
        {}
    );
    await getService("view").loadViews(
        {
            resModel: "take.five",
            views: [[99, "list"]],
            context: { default_field_value: 2 },
        },
        {}
    );
    expect.verifySteps(["get_views"]);
});

test("stores calls in cache when failed", async () => {
    expect.assertions(3);
    onRpc("get_views", () => {
        expect.step("get_views");
        throw new Error("my little error");
    });
    await makeMockEnv();
    await expect(
        getService("view").loadViews(
            {
                resModel: "take.five",
                views: [[99, "list"]],
            },
            {}
        )
    ).rejects.toThrow(/my little error/);
    await expect(
        getService("view").loadViews(
            {
                resModel: "take.five",
                views: [[99, "list"]],
            },
            {}
        )
    ).rejects.toThrow(/my little error/);
    expect.verifySteps(["get_views", "get_views"]);
});

test("clear cache when updating ir.ui.view", async () => {
    expect.assertions(4);
    onRpc("get_views", () => {
        expect.step("get_views");
    });
    await makeMockEnv();
    const loadView = () =>
        getService("view").loadViews(
            {
                resModel: "take.five",
                views: [[99, "list"]],
                context: { default_field_value: 1 },
            },
            {}
        );
    await loadView();
    expect.verifySteps(["get_views"]);
    await loadView();
    expect.verifySteps([]); // cache works => no actual rpc
    await getService("orm").unlink("ir.ui.view", [3]);
    await loadView();
    expect.verifySteps(["get_views"]); // cache was invalidated
    await getService("orm").unlink("take.five", [3]);
    await loadView();
    expect.verifySteps([]); // cache was not invalidated
});
