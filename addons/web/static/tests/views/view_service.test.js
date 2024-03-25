/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import {
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
    expect(["get_views"]).toVerifySteps();
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
    expect(["get_views", "get_views"]).toVerifySteps();
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
    expect(["get_views"]).toVerifySteps();
    await loadView();
    expect([]).toVerifySteps(); // cache works => no actual rpc
    await getService("orm").unlink("ir.ui.view", [3]);
    await loadView();
    expect(["get_views"]).toVerifySteps(); // cache was invalidated
    await getService("orm").unlink("take.five", [3]);
    await loadView();
    expect([]).toVerifySteps(); // cache was not invalidated
});
