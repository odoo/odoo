import { describe, expect, getFixture, test } from "@odoo/hoot";
import { click, on } from "@odoo/hoot-dom";
import { mockMatchMedia, tick } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import {
    parseHash,
    parseSearchQuery,
    router,
    routerBus,
    startRouter,
    stateToUrl,
    urlToState,
} from "@web/core/browser/router";
import { redirect } from "@web/core/utils/urls";

const _urlToState = (url) => urlToState(new URL(url));

function createRouter(params = {}) {
    if (params.onPushState) {
        patchWithCleanup(browser.history, {
            pushState() {
                super.pushState(...arguments);
                params.onPushState(...arguments);
            },
        });
    }
    if (params.onReplaceState) {
        patchWithCleanup(browser.history, {
            replaceState() {
                super.replaceState(...arguments);
                params.onReplaceState(...arguments);
            },
        });
    }
    startRouter();
}

describe.current.tags("headless");

describe("parseHash", () => {
    test("can parse an empty hash", () => {
        expect(parseHash("")).toEqual({});
    });

    test("can parse an single hash", () => {
        expect(parseHash("#")).toEqual({});
    });

    test("can parse a hash with a single key/value pair", () => {
        expect(parseHash("#action=114")).toEqual({ action: 114 });
    });

    test("can parse a hash with 2 key/value pairs", () => {
        expect(parseHash("#action=114&active_id=mail.box_inbox")).toEqual({
            action: 114,
            active_id: "mail.box_inbox",
        });
    });

    test("a missing value is encoded as an empty string", () => {
        expect(parseHash("#action")).toEqual({ action: "" });
    });

    test("a missing value is encoded as an empty string -- 2", () => {
        expect(parseHash("#action=")).toEqual({ action: "" });
    });

    test("can parse a realistic hash", () => {
        expect(parseHash("#action=114&active_id=mail.box_inbox&menu_id=91")).toEqual({
            action: 114,
            active_id: "mail.box_inbox",
            menu_id: 91,
        });
    });

    test("can parse URI encoded strings", () => {
        expect(parseHash("#comma=that%2Cis")).toEqual({ comma: "that,is" });
    });
});

describe("parseSearchQuery", () => {
    test("can parse an empty search", () => {
        expect(parseSearchQuery("")).toEqual({});
    });

    test("can parse an simple search with no value", () => {
        expect(parseSearchQuery("?a")).toEqual({ a: "" });
    });

    test("can parse an simple search with a value", () => {
        expect(parseSearchQuery("?a=1")).toEqual({ a: 1 });
    });

    test("can parse an search with 2 key/value pairs", () => {
        expect(parseSearchQuery("?a=1&b=2")).toEqual({ a: 1, b: 2 });
    });

    test("can parse URI encoded strings", () => {
        expect(parseHash("#comma=that%2Cis")).toEqual({ comma: "that,is" });
    });
});

describe("stateToUrl", () => {
    test("encodes URI compatible strings", (assert) => {
        expect(stateToUrl({})).toBe("/odoo");
        expect(stateToUrl({ a: "11", b: "summer wine" })).toBe("/odoo?a=11&b=summer%20wine");
        expect(stateToUrl({ b: "2", c: "", e: "kloug,gloubi" })).toBe(
            "/odoo?b=2&c=&e=kloug%2Cgloubi"
        );
    });

    test("backwards compatibility: no action stack, action encoded in path", (assert) => {
        expect(stateToUrl({})).toBe("/odoo");
        // action
        expect(stateToUrl({ action: "some-path" })).toBe("/odoo/some-path");
        expect(stateToUrl({ active_id: 5, action: "some-path" })).toBe("/odoo/5/some-path");
        expect(stateToUrl({ active_id: "some-active_id", action: "some-path" })).toBe(
            "/odoo/some-path?active_id=some-active_id",
            { message: "only numeric active_id are encoded in path" }
        );
        expect(stateToUrl({ action: "some-path", resId: 2 })).toBe("/odoo/some-path/2");
        expect(stateToUrl({ action: "some-path", resId: "some-resId" })).toBe(
            "/odoo/some-path?resId=some-resId",
            { message: "only numeric resId are encoded in path" }
        );
        expect(stateToUrl({ active_id: 5, action: "some-path", resId: 2 })).toBe(
            "/odoo/5/some-path/2"
        );
        expect(stateToUrl({ active_id: 5, action: "some-path", resId: "new" })).toBe(
            "/odoo/5/some-path/new"
        );
        expect(stateToUrl({ action: 1, resId: 2 })).toBe("/odoo/action-1/2", {
            message: "action id instead of path/tag",
        });
        expect(stateToUrl({ action: "module.xml_id", resId: 2 })).toBe(
            "/odoo/action-module.xml_id/2",
            { message: "action xml_id instead of path/tag" }
        );
        // model
        expect(stateToUrl({ model: "some.model" })).toBe("/odoo/some.model");
        expect(stateToUrl({ model: "some.model", resId: 2 })).toBe("/odoo/some.model/2");
        expect(stateToUrl({ active_id: 5, model: "some.model" })).toBe("/odoo/5/some.model");
        expect(stateToUrl({ active_id: 5, model: "some.model", resId: 2 })).toBe(
            "/odoo/5/some.model/2"
        );
        expect(stateToUrl({ active_id: 5, model: "some.model", resId: "new" })).toBe(
            "/odoo/5/some.model/new"
        );
        expect(stateToUrl({ active_id: 5, model: "some.model", view_type: "some_viewtype" })).toBe(
            "/odoo/5/some.model?view_type=some_viewtype"
        );
        // edge cases
        expect(
            stateToUrl({ active_id: 5, action: "some-path", resId: 2, some_key: "some_value" })
        ).toBe("/odoo/5/some-path/2?some_key=some_value", {
            message: "pieces of state unrelated to actions are added as query string",
        });
        expect(
            stateToUrl({ active_id: 5, action: "some-path", model: "some.model", resId: 2 })
        ).toBe("/odoo/5/some-path/2", { message: "action has priority on model" });
        expect(stateToUrl({ active_id: 5, model: "some.model", resId: 2, view_type: "list" })).toBe(
            "/odoo/5/some.model/2?view_type=list",
            { message: "view_type and resId aren't incompatible" }
            // Should they be? view_type will just be stripped by action_service
        );
    });

    test("actionStack: one action", () => {
        expect(stateToUrl({ actionStack: [] })).toBe("/odoo");
        // action
        expect(stateToUrl({ actionStack: [{ action: "some-path" }] })).toBe("/odoo/some-path");
        expect(stateToUrl({ actionStack: [{ active_id: 5, action: "some-path" }] })).toBe(
            "/odoo/5/some-path"
        );
        expect(stateToUrl({ actionStack: [{ action: "some-path", resId: 2 }] })).toBe(
            "/odoo/some-path/2"
        );
        expect(stateToUrl({ actionStack: [{ active_id: 5, action: "some-path", resId: 2 }] })).toBe(
            "/odoo/5/some-path/2"
        );
        expect(
            stateToUrl({ actionStack: [{ active_id: 5, action: "some-path", resId: "new" }] })
        ).toBe("/odoo/5/some-path/new");
        expect(stateToUrl({ actionStack: [{ action: 1, resId: 2 }] })).toBe("/odoo/action-1/2", {
            message: "numerical action id instead of path",
        });
        expect(stateToUrl({ actionStack: [{ action: "module.xml_id", resId: 2 }] })).toBe(
            "/odoo/action-module.xml_id/2",
            { message: "action xml_id instead of path" }
        );
        // model
        expect(stateToUrl({ actionStack: [{ model: "some.model" }] })).toBe("/odoo/some.model");
        expect(stateToUrl({ actionStack: [{ model: "some.model", resId: 2 }] })).toBe(
            "/odoo/some.model/2"
        );
        expect(stateToUrl({ actionStack: [{ active_id: 5, model: "some.model" }] })).toBe(
            "/odoo/5/some.model"
        );
        expect(stateToUrl({ actionStack: [{ active_id: 5, model: "some.model", resId: 2 }] })).toBe(
            "/odoo/5/some.model/2"
        );
        expect(
            stateToUrl({ actionStack: [{ active_id: 5, model: "some.model", resId: "new" }] })
        ).toBe("/odoo/5/some.model/new");
        expect(
            stateToUrl({
                actionStack: [{ active_id: 5, model: "some.model", view_type: "some_viewtype" }],
            })
        ).toBe("/odoo/5/some.model", { message: "view_type is ignored in the action stack" });
        expect(
            stateToUrl({
                actionStack: [{ active_id: 5, model: "some.model" }],
                view_type: "some_viewtype",
            })
        ).toBe("/odoo/5/some.model?view_type=some_viewtype", {
            message: "view_type is added if it's on the state itself",
        });
        expect(
            stateToUrl({ actionStack: [{ active_id: 5, model: "model_no_dot", resId: 2 }] })
        ).toBe("/odoo/5/m-model_no_dot/2");
        // edge cases
        expect(
            stateToUrl({
                actionStack: [
                    { active_id: 5, action: "some-path", resId: 2, some_key: "some_value" },
                ],
            })
        ).toBe("/odoo/5/some-path/2", {
            message: "pieces of state unrelated to actions are ignored in the actionStack",
        });
        expect(
            stateToUrl({
                actionStack: [{ active_id: 5, action: "some-path", resId: 2 }],
                some_key: "some_value",
            })
        ).toBe("/odoo/5/some-path/2?some_key=some_value", {
            message:
                "pieces of state unrelated to actions are added as query string even with actionStack",
        });
        expect(
            stateToUrl({
                actionStack: [{ active_id: 5, action: "some-path", model: "some.model", resId: 2 }],
            })
        ).toBe("/odoo/5/some-path/2", { message: "action has priority on model" });
        expect(
            stateToUrl({
                actionStack: [{ active_id: 5, model: "some.model", resId: 2 }],
                view_type: "list",
            })
        ).toBe(
            "/odoo/5/some.model/2?view_type=list",
            { message: "view_type and resId aren't incompatible" }
            // Should they be? view_type will just be stripped by action_service
        );
    });

    test("actionStack: multiple actions", () => {
        // different actions
        expect(
            stateToUrl({ actionStack: [{ action: "some-path" }, { action: "other-path" }] })
        ).toBe("/odoo/some-path/other-path");
        expect(
            stateToUrl({
                actionStack: [{ active_id: 5, action: "some-path" }, { action: "other-path" }],
            })
        ).toBe("/odoo/5/some-path/other-path");
        expect(
            stateToUrl({
                actionStack: [{ action: "some-path" }, { active_id: 7, action: "other-path" }],
            })
        ).toBe(
            // On reload, this will generate a form view for the first action even though there was
            // originally none. This is probably fine.
            "/odoo/some-path/7/other-path"
        );
        expect(
            stateToUrl({
                actionStack: [{ action: "some-path", resId: 2 }, { action: "other-path" }],
            })
        ).toBe(
            // On reload, the second action will have an active_id even though it originally didn't
            // have one. This might be a problem?
            "/odoo/some-path/2/other-path"
        );
        expect(
            stateToUrl({
                actionStack: [{ action: "some-path" }, { action: "other-path", resId: 2 }],
            })
        ).toBe(
            // On reload, this will generate an action in the default multi-record view for the second
            // action. This is the desired behaviour.
            "/odoo/some-path/other-path/2"
        );
        expect(
            stateToUrl({
                actionStack: [
                    { active_id: 5, action: "some-path", resId: 2 },
                    { action: "other-path" },
                ],
            })
        ).toBe("/odoo/5/some-path/2/other-path");
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path" },
                    { active_id: 5, action: "other-path", resId: 2 },
                ],
            })
        ).toBe("/odoo/some-path/5/other-path/2");
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path" },
                    { active_id: 5, action: "other-path", resId: "new" },
                ],
            })
        ).toBe("/odoo/some-path/5/other-path/new");
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, action: "other-path" },
                ],
            })
        ).toBe("/odoo/some-path/5/other-path", {
            message:
                "action with resId followed by action with same value as active_id is not duplicated",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, action: "other-path", resId: 2 },
                ],
            })
        ).toBe("/odoo/some-path/5/other-path/2");
        expect(
            stateToUrl({
                actionStack: [{ action: 1 }, { active_id: 5, action: 6, resId: 2 }],
            })
        ).toBe("/odoo/action-1/5/action-6/2", { message: "numerical actions" });
        expect(
            stateToUrl({
                actionStack: [
                    { action: "module.xml_id" },
                    { active_id: 5, action: "module.other_xml_id", resId: 2 },
                ],
            })
        ).toBe("/odoo/action-module.xml_id/5/action-module.other_xml_id/2", {
            message: "actions as xml_ids",
        });
        // same action twice
        expect(
            stateToUrl({ actionStack: [{ action: "some-path" }, { action: "some-path" }] })
        ).toBe("/odoo/some-path", {
            message: "consolidates identical actions into one path segment",
        });
        expect(
            stateToUrl({
                actionStack: [{ active_id: 5, action: "some-path" }, { action: "some-path" }],
            })
        ).toBe("/odoo/5/some-path/some-path", {
            message: "doesn't consolidate the same action with different active_id",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 7 },
                    { active_id: 7, action: "some-path" },
                ],
            })
        ).toBe("/odoo/some-path/7/some-path", {
            message:
                "doesn't remove multirecord action if it follows the same action in mono-record mode",
        });
        expect(
            stateToUrl({
                actionStack: [{ action: "some-path", resId: 2 }, { action: "some-path" }],
            })
        ).toBe("/odoo/some-path/2/some-path");
        expect(
            stateToUrl({
                actionStack: [
                    { active_id: 7, action: "some-path", resId: 7 },
                    { active_id: 7, action: "some-path" },
                ],
            })
        ).toBe("/odoo/7/some-path/7/some-path", {
            message:
                "doesn't remove multirecord action if it follows the same action in mono-record mode even if the active_id are the same",
        });
        expect(
            stateToUrl({
                actionStack: [{ action: "some-path" }, { action: "some-path", resId: 2 }],
            })
        ).toBe("/odoo/some-path/2", {
            message: "consolidates multi-record action with mono-record action",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { active_id: 5, action: "some-path" },
                    { active_id: 5, action: "some-path", resId: 2 },
                ],
            })
        ).toBe("/odoo/5/some-path/2", {
            message:
                "consolidates multi-record action with mono-record action if they have the same active_id",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { active_id: 5, action: "some-path", resId: 2 },
                    { action: "some-path" },
                ],
            })
        ).toBe("/odoo/5/some-path/2/some-path");
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path" },
                    { active_id: 5, action: "some-path", resId: 2 },
                ],
            })
        ).toBe("/odoo/some-path/5/some-path/2", {
            message:
                "doesn't consolidate mono-record action into preceding multi-record action if active_id is not the same",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path" },
                    { active_id: 5, action: "some-path", resId: "new" },
                ],
            })
        ).toBe("/odoo/some-path/5/some-path/new");
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, action: "some-path" },
                ],
            })
        ).toBe("/odoo/some-path/5/some-path", {
            message:
                "action with resId followed by action with same value as active_id is not duplicated",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, action: "some-path", resId: 2 },
                ],
            })
        ).toBe("/odoo/some-path/5/some-path/2", {
            message: "doesn't consolidate two mono-record actions",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { active_id: 5, action: "some-path", resId: 5 },
                    { active_id: 5, action: "some-path", resId: 2 },
                ],
            })
        ).toBe("/odoo/5/some-path/5/some-path/2", {
            message: "doesn't consolidate two mono-record actions even with same active_id",
        });
        expect(
            stateToUrl({
                actionStack: [{ action: 1 }, { active_id: 5, action: 1, resId: 2 }],
            })
        ).toBe("/odoo/action-1/5/action-1/2", { message: "numerical actions" });
        expect(
            stateToUrl({
                actionStack: [
                    { action: "module.xml_id" },
                    { active_id: 5, action: "module.xml_id", resId: 2 },
                ],
            })
        ).toBe("/odoo/action-module.xml_id/5/action-module.xml_id/2", {
            message: "actions as xml_ids",
        });
        // model
        expect(
            stateToUrl({ actionStack: [{ model: "some.model" }, { model: "other.model" }] })
        ).toBe("/odoo/some.model/other.model");
        expect(
            stateToUrl({
                actionStack: [{ active_id: 5, model: "some.model" }, { model: "other.model" }],
            })
        ).toBe("/odoo/5/some.model/other.model");
        expect(
            stateToUrl({
                actionStack: [{ model: "some.model" }, { active_id: 7, model: "other.model" }],
            })
        ).toBe("/odoo/some.model/7/other.model");
        expect(
            stateToUrl({
                actionStack: [{ model: "some.model", resId: 2 }, { model: "other.model" }],
            })
        ).toBe("/odoo/some.model/2/other.model");
        expect(
            stateToUrl({
                actionStack: [{ model: "some.model" }, { model: "other.model", resId: 2 }],
            })
        ).toBe("/odoo/some.model/other.model/2");
        expect(
            stateToUrl({
                actionStack: [
                    { active_id: 5, model: "some.model", resId: 2 },
                    { model: "other.model" },
                ],
            })
        ).toBe("/odoo/5/some.model/2/other.model");
        expect(
            stateToUrl({
                actionStack: [
                    { model: "some.model" },
                    { active_id: 5, model: "other.model", resId: 2 },
                ],
            })
        ).toBe("/odoo/some.model/5/other.model/2");
        expect(
            stateToUrl({
                actionStack: [
                    { model: "some.model" },
                    { active_id: 5, model: "other.model", resId: "new" },
                ],
            })
        ).toBe("/odoo/some.model/5/other.model/new");
        expect(
            stateToUrl({
                actionStack: [
                    { model: "some.model", resId: 5 },
                    { active_id: 5, model: "other.model" },
                ],
            })
        ).toBe("/odoo/some.model/5/other.model", {
            message:
                "action with resId followed by action with same value as active_id is not duplicated",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { model: "some.model", resId: 5 },
                    { active_id: 5, model: "other.model", resId: 2 },
                ],
            })
        ).toBe("/odoo/some.model/5/other.model/2");
        expect(
            stateToUrl({
                actionStack: [
                    { model: "model_no_dot", resId: 5 },
                    { active_id: 5, model: "no_dot_model", resId: 2 },
                ],
            })
        ).toBe("/odoo/m-model_no_dot/5/m-no_dot_model/2");
        // action + model
        expect(
            stateToUrl({ actionStack: [{ action: "some-path" }, { model: "some.model" }] })
        ).toBe("/odoo/some-path/some.model");
        expect(
            stateToUrl({
                actionStack: [{ active_id: 5, action: "some-path" }, { model: "some.model" }],
            })
        ).toBe("/odoo/5/some-path/some.model");
        expect(
            stateToUrl({
                actionStack: [{ action: "some-path" }, { active_id: 7, model: "some.model" }],
            })
        ).toBe("/odoo/some-path/7/some.model");
        expect(
            stateToUrl({
                actionStack: [{ action: "some-path", resId: 2 }, { model: "some.model" }],
            })
        ).toBe("/odoo/some-path/2/some.model");
        expect(
            stateToUrl({
                actionStack: [{ action: "some-path" }, { model: "some.model", resId: 2 }],
            })
        ).toBe("/odoo/some-path/some.model/2");
        expect(
            stateToUrl({
                actionStack: [
                    { active_id: 5, action: "some-path", resId: 2 },
                    { model: "some.model" },
                ],
            })
        ).toBe("/odoo/5/some-path/2/some.model");
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path" },
                    { active_id: 5, model: "some.model", resId: 2 },
                ],
            })
        ).toBe("/odoo/some-path/5/some.model/2");
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path" },
                    { active_id: 5, model: "some.model", resId: "new" },
                ],
            })
        ).toBe("/odoo/some-path/5/some.model/new");
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, model: "some.model" },
                ],
            })
        ).toBe("/odoo/some-path/5/some.model", {
            message:
                "action with resId followed by action with same value as active_id is not duplicated",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, model: "some.model", resId: 2 },
                ],
            })
        ).toBe("/odoo/some-path/5/some.model/2");
        expect(
            stateToUrl({
                actionStack: [
                    { action: 1, resId: 5 },
                    { active_id: 5, model: "model_no_dot", resId: 2 },
                ],
            })
        ).toBe("/odoo/action-1/5/m-model_no_dot/2");
        expect(
            stateToUrl({
                actionStack: [
                    { action: "module.xml_id", resId: 5 },
                    { active_id: 5, model: "model_no_dot", resId: 2 },
                ],
            })
        ).toBe("/odoo/action-module.xml_id/5/m-model_no_dot/2");
        // model + action
        expect(
            stateToUrl({ actionStack: [{ model: "some.model" }, { action: "other-path" }] })
        ).toBe("/odoo/some.model/other-path");
        expect(
            stateToUrl({
                actionStack: [{ active_id: 5, model: "some.model" }, { action: "other-path" }],
            })
        ).toBe("/odoo/5/some.model/other-path");
        expect(
            stateToUrl({
                actionStack: [{ model: "some.model" }, { active_id: 7, action: "other-path" }],
            })
        ).toBe("/odoo/some.model/7/other-path");
        expect(
            stateToUrl({
                actionStack: [{ model: "some.model", resId: 2 }, { action: "other-path" }],
            })
        ).toBe("/odoo/some.model/2/other-path");
        expect(
            stateToUrl({
                actionStack: [{ model: "some.model" }, { action: "other-path", resId: 2 }],
            })
        ).toBe("/odoo/some.model/other-path/2");
        expect(
            stateToUrl({
                actionStack: [
                    { active_id: 5, model: "some.model", resId: 2 },
                    { action: "other-path" },
                ],
            })
        ).toBe("/odoo/5/some.model/2/other-path");
        expect(
            stateToUrl({
                actionStack: [
                    { model: "some.model" },
                    { active_id: 5, action: "other-path", resId: 2 },
                ],
            })
        ).toBe("/odoo/some.model/5/other-path/2");
        expect(
            stateToUrl({
                actionStack: [
                    { model: "some.model" },
                    { active_id: 5, action: "other-path", resId: "new" },
                ],
            })
        ).toBe("/odoo/some.model/5/other-path/new");
        expect(
            stateToUrl({
                actionStack: [
                    { model: "some.model", resId: 5 },
                    { active_id: 5, action: "other-path" },
                ],
            })
        ).toBe("/odoo/some.model/5/other-path", {
            message:
                "action with resId followed by action with same value as active_id is not duplicated",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { model: "some.model", resId: 5 },
                    { active_id: 5, action: "other-path", resId: 2 },
                ],
            })
        ).toBe("/odoo/some.model/5/other-path/2");
        expect(
            stateToUrl({
                actionStack: [
                    { model: "model_no_dot", resId: 5 },
                    { active_id: 5, action: 1, resId: 2 },
                ],
            })
        ).toBe("/odoo/m-model_no_dot/5/action-1/2");
        expect(
            stateToUrl({
                actionStack: [
                    { model: "model_no_dot", resId: 5 },
                    { active_id: 5, action: "module.xml_id", resId: 2 },
                ],
            })
        ).toBe("/odoo/m-model_no_dot/5/action-module.xml_id/2");

        // edge cases
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5, some_key: "some_value" },
                    { active_id: 5, action: "other-path", resId: 2, other_key: "other_value" },
                ],
            })
        ).toBe("/odoo/some-path/5/other-path/2", {
            message: "pieces of state unrelated to actions are ignored in the actionStack",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, action: "other-path", resId: 2 },
                ],
                some_key: "some_value",
            })
        ).toBe("/odoo/some-path/5/other-path/2?some_key=some_value", {
            message:
                "pieces of state unrelated to actions are added as query string even with actionStack",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path", model: "some.model", resId: 5 },
                    { active_id: 5, action: "other-path", model: "other.model", resId: 2 },
                ],
            })
        ).toBe("/odoo/some-path/5/other-path/2", { message: "action has priority on model" });
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, model: "some.model", resId: 2 },
                ],
                view_type: "list",
            })
        ).toBe("/odoo/some-path/5/some.model/2?view_type=list", {
            message: "view_type and resId aren't incompatible",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 2 },
                    { active_id: 5, action: "other-path" },
                ],
            })
        ).toBe("/odoo/some-path/2/5/other-path", {
            message:
                "action with resId followed by action with different active_id gets both ids in a row",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { model: "some.model", resId: 2 },
                    { active_id: 5, model: "other.model" },
                ],
            })
        ).toBe("/odoo/some.model/2/5/other.model", {
            message:
                "action with resId followed by action with different active_id gets both ids in a row",
        });
        expect(
            stateToUrl({
                actionStack: [
                    { action: "other-path", resId: 5 },
                    { active_id: 5, action: "some-path" },
                    { active_id: 5, action: "some-path", resId: 2 },
                ],
            })
        ).toBe("/odoo/other-path/5/some-path/2", {
            message:
                "active_id of last action is correctly removed even if previous action's active id is also removed because of the preceding resId",
        });
    });
});

describe("urlToState", () => {
    test("deserialize queryString", () => {
        expect(_urlToState("/odoo?a=11&g=summer%20wine")).toEqual({
            a: 11,
            g: "summer wine",
        });
        expect(_urlToState("/odoo?g=2&c=&e=kloug%2Cgloubi")).toEqual({
            g: 2,
            c: "",
            e: "kloug,gloubi",
        });
    });

    test("deserialize action in legacy url form", () => {
        expect(
            _urlToState("/web#id=5&action=1&model=some.model&view_type=form&menu_id=137&cids=1")
        ).toEqual({
            action: 1,
            resId: 5,
            cids: 1,
            menu_id: 137,
            model: "some.model",
            actionStack: [
                {
                    action: 1,
                },
                {
                    action: 1,
                    resId: 5,
                },
            ],
        });

        expect(_urlToState("/web#id=5&model=some.model&view_type=form&menu_id=137&cids=1")).toEqual(
            {
                resId: 5,
                cids: 1,
                menu_id: 137,
                model: "some.model",
                actionStack: [
                    {
                        resId: 5,
                        model: "some.model",
                    },
                ],
            },
            { message: "no action" }
        );
    });

    test("deserialize single action", () => {
        expect(_urlToState("")).toEqual({});
        expect(_urlToState("/odoo")).toEqual({});
        // action
        expect(_urlToState("/odoo/some-path")).toEqual({
            action: "some-path",
            actionStack: [{ action: "some-path" }],
        });
        expect(_urlToState("/odoo/5/some-path")).toEqual({
            active_id: 5,
            action: "some-path",
            actionStack: [{ active_id: 5, action: "some-path" }],
        });
        expect(_urlToState("/odoo/some-path/2")).toEqual(
            {
                action: "some-path",
                resId: 2,
                actionStack: [{ action: "some-path" }, { action: "some-path", resId: 2 }],
            },
            { message: "two actions are created for action with resId" }
        );
        expect(_urlToState("/odoo/some-path/new")).toEqual(
            {
                action: "some-path",
                resId: "new",
                actionStack: [{ action: "some-path" }, { action: "some-path", resId: "new" }],
            },
            { message: "new record" }
        );
        expect(_urlToState("/odoo/5/some-path/2")).toEqual({
            active_id: 5,
            action: "some-path",
            resId: 2,
            actionStack: [
                {
                    active_id: 5,
                    action: "some-path",
                },
                {
                    active_id: 5,
                    action: "some-path",
                    resId: 2,
                },
            ],
        });
        expect(_urlToState("/odoo/action-1/2")).toEqual({
            action: 1,
            resId: 2,
            actionStack: [{ action: 1 }, { action: 1, resId: 2 }],
        });
        expect(_urlToState("/odoo/action-module.xml_id/2")).toEqual({
            action: "module.xml_id",
            resId: 2,
            actionStack: [{ action: "module.xml_id" }, { action: "module.xml_id", resId: 2 }],
        });
        // model
        expect(_urlToState("/odoo/some.model")).toEqual({
            model: "some.model",
            actionStack: [{ model: "some.model" }],
        });
        expect(_urlToState("/odoo/some.model/2")).toEqual(
            {
                model: "some.model",
                resId: 2,
                actionStack: [{ model: "some.model", resId: 2 }],
            },
            { message: "single action is created for model with resId" }
        );
        expect(_urlToState("/odoo/some.model/new")).toEqual(
            {
                model: "some.model",
                resId: "new",
                actionStack: [{ model: "some.model", resId: "new" }],
            },
            { message: "new record" }
        );
        expect(_urlToState("/odoo/5/some.model")).toEqual({
            active_id: 5,
            model: "some.model",
            actionStack: [{ active_id: 5, model: "some.model" }],
        });
        expect(_urlToState("/odoo/5/some.model/2")).toEqual({
            active_id: 5,
            model: "some.model",
            resId: 2,
            actionStack: [{ active_id: 5, model: "some.model", resId: 2 }],
        });
        expect(_urlToState("/odoo/5/some.model?view_type=some_viewtype")).toEqual(
            {
                active_id: 5,
                model: "some.model",
                view_type: "some_viewtype",
                actionStack: [{ active_id: 5, model: "some.model" }],
            },
            { message: "view_type doesn't end up in the actionStack" }
        );
        expect(_urlToState("/odoo/m-model_no_dot/2")).toEqual({
            model: "model_no_dot",
            resId: 2,
            actionStack: [{ model: "model_no_dot", resId: 2 }],
        });
        // edge cases
        expect(_urlToState("/odoo/5/some-path/2?some_key=some_value")).toEqual(
            {
                active_id: 5,
                action: "some-path",
                resId: 2,
                some_key: "some_value",
                actionStack: [
                    { active_id: 5, action: "some-path" },
                    { active_id: 5, action: "some-path", resId: 2 },
                ],
            },
            {
                message:
                    "pieces of state unrelated to actions end up on the state but not in the actionStack",
            }
        );
        expect(_urlToState("/odoo/5/some.model/2?view_type=list")).toEqual(
            {
                active_id: 5,
                model: "some.model",
                resId: 2,
                view_type: "list",
                actionStack: [{ active_id: 5, model: "some.model", resId: 2 }],
            },
            { message: "view_type and resId aren't incompatible" }
        );
    });

    test("deserialize multiple actions", () => {
        // action
        expect(_urlToState("/odoo/some-path/other-path")).toEqual({
            action: "other-path",
            actionStack: [{ action: "some-path" }, { action: "other-path" }],
        });
        expect(_urlToState("/odoo/5/some-path/other-path")).toEqual({
            action: "other-path",
            actionStack: [{ active_id: 5, action: "some-path" }, { action: "other-path" }],
        });
        expect(_urlToState("/odoo/some-path/2/other-path")).toEqual({
            action: "other-path",
            active_id: 2,
            actionStack: [
                { action: "some-path" },
                { action: "some-path", resId: 2 },
                { active_id: 2, action: "other-path" },
            ],
        });
        expect(_urlToState("/odoo/some-path/other-path/2")).toEqual({
            action: "other-path",
            resId: 2,
            actionStack: [
                { action: "some-path" },
                { action: "other-path" },
                { action: "other-path", resId: 2 },
            ],
        });
        expect(_urlToState("/odoo/5/some-path/2/other-path")).toEqual({
            action: "other-path",
            active_id: 2,
            actionStack: [
                { active_id: 5, action: "some-path" },
                { active_id: 5, action: "some-path", resId: 2 },
                { active_id: 2, action: "other-path" },
            ],
        });
        expect(_urlToState("/odoo/some-path/5/other-path/2")).toEqual({
            active_id: 5,
            action: "other-path",
            resId: 2,
            actionStack: [
                { action: "some-path" },
                { action: "some-path", resId: 5 },
                { active_id: 5, action: "other-path" },
                { active_id: 5, action: "other-path", resId: 2 },
            ],
        });
        expect(_urlToState("/odoo/some-path/5/other-path/new")).toEqual({
            active_id: 5,
            action: "other-path",
            resId: "new",
            actionStack: [
                { action: "some-path" },
                { action: "some-path", resId: 5 },
                { active_id: 5, action: "other-path" },
                { active_id: 5, action: "other-path", resId: "new" },
            ],
        });
        expect(_urlToState("/odoo/action-1/5/action-6/2")).toEqual({
            active_id: 5,
            action: 6,
            resId: 2,
            actionStack: [
                { action: 1 },
                { action: 1, resId: 5 },
                { active_id: 5, action: 6 },
                { active_id: 5, action: 6, resId: 2 },
            ],
        });
        expect(_urlToState("/odoo/action-module.xml_id/5/action-module.other_xml_id/2")).toEqual({
            active_id: 5,
            action: "module.other_xml_id",
            resId: 2,
            actionStack: [
                { action: "module.xml_id" },
                { action: "module.xml_id", resId: 5 },
                { active_id: 5, action: "module.other_xml_id" },
                { active_id: 5, action: "module.other_xml_id", resId: 2 },
            ],
        });
        // model
        expect(_urlToState("/odoo/some.model/other.model")).toEqual(
            {
                model: "other.model",
                actionStack: [{ model: "other.model" }],
            },
            {
                message:
                    "model not followed by resId doesn't generate an action unless it's the last one",
            }
        );
        expect(_urlToState("/odoo/5/some.model/other.model")).toEqual(
            {
                model: "other.model",
                actionStack: [{ model: "other.model" }],
            },
            {
                message:
                    "model not followed by resId doesn't generate an action unless it's the last one, even with an active_id",
            }
        );
        expect(_urlToState("/odoo/some.model/7/other.model")).toEqual({
            active_id: 7,
            model: "other.model",
            actionStack: [
                { model: "some.model", resId: 7 },
                { active_id: 7, model: "other.model" },
            ],
        });
        expect(_urlToState("/odoo/some.model/other.model/2")).toEqual({
            model: "other.model",
            resId: 2,
            actionStack: [{ model: "other.model", resId: 2 }],
        });
        expect(_urlToState("/odoo/5/some.model/2/other.model")).toEqual({
            active_id: 2,
            model: "other.model",
            actionStack: [
                { active_id: 5, model: "some.model", resId: 2 },
                { active_id: 2, model: "other.model" },
            ],
        });
        expect(_urlToState("/odoo/some.model/5/other.model/2")).toEqual({
            active_id: 5,
            model: "other.model",
            resId: 2,
            actionStack: [
                { model: "some.model", resId: 5 },
                { active_id: 5, model: "other.model", resId: 2 },
            ],
        });
        expect(_urlToState("/odoo/some.model/5/other.model/new")).toEqual({
            active_id: 5,
            model: "other.model",
            resId: "new",
            actionStack: [
                { model: "some.model", resId: 5 },
                { active_id: 5, model: "other.model", resId: "new" },
            ],
        });
        expect(_urlToState("/odoo/m-model_no_dot/5/m-no_dot_model/2")).toEqual({
            active_id: 5,
            model: "no_dot_model",
            resId: 2,
            actionStack: [
                { model: "model_no_dot", resId: 5 },
                { active_id: 5, model: "no_dot_model", resId: 2 },
            ],
        });
        // action + model
        expect(_urlToState("/odoo/some-path/some.model")).toEqual({
            model: "some.model",
            actionStack: [{ action: "some-path" }, { model: "some.model" }],
        });
        expect(_urlToState("/odoo/5/some-path/some.model")).toEqual({
            model: "some.model",
            actionStack: [{ active_id: 5, action: "some-path" }, { model: "some.model" }],
        });
        expect(_urlToState("/odoo/some-path/7/some.model")).toEqual({
            active_id: 7,
            model: "some.model",
            actionStack: [
                { action: "some-path" },
                { action: "some-path", resId: 7 },
                { active_id: 7, model: "some.model" },
            ],
        });
        expect(_urlToState("/odoo/some-path/some.model/2")).toEqual({
            model: "some.model",
            resId: 2,
            actionStack: [{ action: "some-path" }, { model: "some.model", resId: 2 }],
        });
        expect(_urlToState("/odoo/5/some-path/2/some.model")).toEqual({
            active_id: 2,
            model: "some.model",
            actionStack: [
                { active_id: 5, action: "some-path" },
                { active_id: 5, action: "some-path", resId: 2 },
                { active_id: 2, model: "some.model" },
            ],
        });
        expect(_urlToState("/odoo/some-path/5/some.model/2")).toEqual({
            active_id: 5,
            model: "some.model",
            resId: 2,
            actionStack: [
                { action: "some-path" },
                { action: "some-path", resId: 5 },
                { active_id: 5, model: "some.model", resId: 2 },
            ],
        });
        expect(_urlToState("/odoo/some-path/5/some.model/new")).toEqual({
            active_id: 5,
            model: "some.model",
            resId: "new",
            actionStack: [
                { action: "some-path" },
                { action: "some-path", resId: 5 },
                { active_id: 5, model: "some.model", resId: "new" },
            ],
        });
        expect(_urlToState("/odoo/action-1/5/m-model_no_dot/2")).toEqual({
            active_id: 5,
            model: "model_no_dot",
            resId: 2,
            actionStack: [
                { action: 1 },
                { action: 1, resId: 5 },
                { active_id: 5, model: "model_no_dot", resId: 2 },
            ],
        });
        expect(_urlToState("/odoo/action-module.xml_id/5/m-model_no_dot/2")).toEqual({
            active_id: 5,
            model: "model_no_dot",
            resId: 2,
            actionStack: [
                { action: "module.xml_id" },
                { action: "module.xml_id", resId: 5 },
                { active_id: 5, model: "model_no_dot", resId: 2 },
            ],
        });
        // model + action
        expect(_urlToState("/odoo/some.model/other-path")).toEqual({
            action: "other-path",
            actionStack: [{ action: "other-path" }],
        });
        expect(_urlToState("/odoo/5/some.model/other-path")).toEqual({
            action: "other-path",
            actionStack: [{ action: "other-path" }],
        });
        expect(_urlToState("/odoo/some.model/2/other-path")).toEqual({
            active_id: 2,
            action: "other-path",
            actionStack: [
                { model: "some.model", resId: 2 },
                { active_id: 2, action: "other-path" },
            ],
        });
        expect(_urlToState("/odoo/some.model/other-path/2")).toEqual({
            action: "other-path",
            resId: 2,
            actionStack: [{ action: "other-path" }, { action: "other-path", resId: 2 }],
        });
        expect(_urlToState("/odoo/5/some.model/2/other-path")).toEqual({
            active_id: 2,
            action: "other-path",
            actionStack: [
                { active_id: 5, model: "some.model", resId: 2 },
                { active_id: 2, action: "other-path" },
            ],
        });
        expect(_urlToState("/odoo/some.model/5/other-path/2")).toEqual({
            active_id: 5,
            action: "other-path",
            resId: 2,
            actionStack: [
                { model: "some.model", resId: 5 },
                { active_id: 5, action: "other-path" },
                { active_id: 5, action: "other-path", resId: 2 },
            ],
        });
        expect(_urlToState("/odoo/some.model/5/other-path/new")).toEqual({
            active_id: 5,
            action: "other-path",
            resId: "new",
            actionStack: [
                { model: "some.model", resId: 5 },
                { active_id: 5, action: "other-path" },
                { active_id: 5, action: "other-path", resId: "new" },
            ],
        });
        expect(_urlToState("/odoo/m-model_no_dot/5/action-1/2")).toEqual({
            active_id: 5,
            action: 1,
            resId: 2,
            actionStack: [
                { model: "model_no_dot", resId: 5 },
                { active_id: 5, action: 1 },
                { active_id: 5, action: 1, resId: 2 },
            ],
        });
        expect(_urlToState("/odoo/m-model_no_dot/5/action-module.xml_id/2")).toEqual({
            active_id: 5,
            action: "module.xml_id",
            resId: 2,
            actionStack: [
                { model: "model_no_dot", resId: 5 },
                { active_id: 5, action: "module.xml_id" },
                { active_id: 5, action: "module.xml_id", resId: 2 },
            ],
        });

        // edge cases
        expect(_urlToState("/odoo/some-path/5/other-path/2?some_key=some_value")).toEqual({
            active_id: 5,
            action: "other-path",
            resId: 2,
            actionStack: [
                { action: "some-path" },
                { action: "some-path", resId: 5 },
                { active_id: 5, action: "other-path" },
                { active_id: 5, action: "other-path", resId: 2 },
            ],
            some_key: "some_value",
        });
        expect(_urlToState("/odoo/some-path/5/some.model?view_type=list")).toEqual(
            {
                active_id: 5,
                model: "some.model",
                actionStack: [
                    { action: "some-path" },
                    { action: "some-path", resId: 5 },
                    { active_id: 5, model: "some.model" },
                ],
                view_type: "list",
            },
            { message: "view_type doesn't end up in the actionStack" }
        );
        expect(_urlToState("/odoo/some-path/5/some.model/2?view_type=list")).toEqual(
            {
                active_id: 5,
                model: "some.model",
                resId: 2,
                actionStack: [
                    { action: "some-path" },
                    { action: "some-path", resId: 5 },
                    { active_id: 5, model: "some.model", resId: 2 },
                ],
                view_type: "list",
            },
            { message: "view_type and resId aren't incompatible" }
        );
        expect(_urlToState("/odoo/some-path/2/5/other-path")).toEqual(
            {
                active_id: 5,
                action: "other-path",
                actionStack: [
                    { action: "some-path" },
                    { action: "some-path", resId: 2 },
                    { active_id: 5, action: "other-path" },
                ],
            },
            { message: "resId immediately following active_id: action" }
        );
        expect(_urlToState("/odoo/some.model/2/5/other.model")).toEqual(
            {
                active_id: 5,
                model: "other.model",
                actionStack: [
                    { model: "some.model", resId: 2 },
                    { active_id: 5, model: "other.model" },
                ],
            },
            { message: "resId immediately following active_id: model" }
        );
    });
});

describe("pushState", () => {
    test("can push in same timeout", async () => {
        createRouter();

        expect(router.current).toEqual({});

        router.pushState({ k1: 2 });
        expect(router.current).toEqual({});

        router.pushState({ k1: 3 });
        expect(router.current).toEqual({});
        await tick();
        expect(router.current).toEqual({ k1: 3 });
    });

    test("can push state directly", async () => {
        createRouter();

        expect(router.current).toEqual({});

        router.pushState({ k1: 2 }, { sync: true });
        expect(router.current).toEqual({ k1: 2 });

        router.pushState({ k1: 3 }, { sync: true });
        expect(router.current).toEqual({ k1: 3 });

        router.pushState({ k1: 4 });
        router.pushState({ k2: 1 }, { sync: true });
        expect(router.current).toEqual({ k1: 4, k2: 1 });
    });

    test("can lock keys", async () => {
        createRouter();

        router.addLockedKey("k1");

        router.replaceState({ k1: 2 });
        await tick();
        expect(router.current).toEqual({ k1: 2 });

        router.replaceState({ k1: 3 });
        await tick();
        expect(router.current).toEqual({ k1: 3 });

        router.replaceState({ k2: 4 });
        await tick();
        expect(router.current).toEqual({ k1: 3, k2: 4 });

        router.replaceState({ k1: 4 });
        await tick();
        expect(router.current).toEqual({ k1: 4, k2: 4 });
    });

    test("can re-lock keys in same final call", async () => {
        createRouter();

        router.addLockedKey("k1");

        router.pushState({ k1: 2 });
        await tick();
        router.pushState({ k2: 1 });
        router.pushState({ k1: 4 });
        await tick();
        expect(router.current).toEqual({ k1: 4, k2: 1 });
    });

    test("can replace search state", async () => {
        createRouter();

        router.pushState({ k1: 2 });
        await tick();
        expect(router.current).toEqual({ k1: 2 });

        router.pushState({ k2: 3 }, { replace: true });
        await tick();
        expect(router.current).toEqual({ k2: 3 });
    });

    test("can replace search state with locked keys", async () => {
        createRouter();

        router.addLockedKey("k1");

        router.pushState({ k1: 2 });
        await tick();
        expect(router.current).toEqual({ k1: 2 });

        router.pushState({ k2: 3 }, { replace: true });
        await tick();
        expect(router.current).toEqual({ k1: 2, k2: 3 });
    });

    test("can merge hash", async () => {
        createRouter();

        router.pushState({ k1: 2 });
        await tick();
        expect(router.current).toEqual({ k1: 2 });

        router.pushState({ k2: 3 });
        await tick();
        expect(router.current).toEqual({ k1: 2, k2: 3 });
    });

    test("undefined keys are not pushed", async () => {
        redirect("/odoo");
        const onPushState = () => expect.step("pushed state");
        createRouter({ onPushState });

        router.pushState({ k1: undefined });
        await tick();
        expect.verifySteps([]);
        expect(router.current).toEqual({});
    });

    test("undefined keys destroy previous non locked keys", async () => {
        createRouter();

        router.pushState({ k1: 1 });
        await tick();
        expect(router.current).toEqual({ k1: 1 });

        router.pushState({ k1: undefined });
        await tick();
        expect(router.current).toEqual({});
    });

    test("do not re-push when hash is same", async () => {
        const onPushState = () => expect.step("pushed state");
        createRouter({ onPushState });

        router.pushState({ k1: 1, k2: 2 });
        await tick();
        expect.verifySteps(["pushed state"]);

        router.pushState({ k2: 2, k1: 1 });
        await tick();
        expect.verifySteps([]);
    });

    test("do not re-push when hash is same (with integers as strings)", async () => {
        const onPushState = () => expect.step("pushed state");
        createRouter({ onPushState });

        router.pushState({ k1: 1, k2: "2" });
        await tick();
        expect.verifySteps(["pushed state"]);

        router.pushState({ k2: 2, k1: "1" });
        await tick();
        expect.verifySteps([]);
    });

    test("pushState adds action-related keys to last entry in actionStack", async () => {
        createRouter();

        router.pushState({ action: 1, resId: 2, actionStack: [{ action: 1, resId: 2 }] });
        await tick();
        expect(router.current).toEqual({
            action: 1,
            resId: 2,
            actionStack: [{ action: 1, resId: 2 }],
        });

        router.pushState({
            action: 3,
            resId: 4,
            view_type: "form",
            model: "some.model",
            active_id: 5,
            someKey: "someVal",
        });
        await tick();
        expect(router.current).toEqual({
            action: 3,
            resId: 4,
            view_type: "form",
            model: "some.model",
            active_id: 5,
            someKey: "someVal",
            actionStack: [
                {
                    action: 3,
                    resId: 4,
                    model: "some.model",
                    active_id: 5,
                },
            ],
        });
    });
    test("can hide keys", async () => {
        createRouter();

        router.hideKeyFromUrl("k1");

        router.pushState({ k1: 2, k2: 3 });
        await tick();
        expect(router.current).toEqual({ k1: 2, k2: 3 });
        expect(browser.location.href).toBe("https://www.hoot.test/odoo?k2=3");
    });
    test("different order of keys shouldn't push a new state", async () => {
        redirect("/odoo?k1=2");
        createRouter({
            onPushState: () => expect.step("pushState"),
        });

        router.addLockedKey("z");
        router.addLockedKey("a");

        router.pushState({ z: 1, a: 2 });
        await tick();
        expect.verifySteps(["pushState"]);
        expect(router.current).toEqual({ a: 2, z: 1, k1: 2 });
        expect(browser.location.href).toBe("https://www.hoot.test/odoo?k1=2&z=1&a=2");

        router.pushState({ k1: 2 }, { replace: true });
        await tick();
        expect.verifySteps([]);
        expect(router.current).toEqual({ a: 2, z: 1, k1: 2 });
        expect(browser.location.href).toBe("https://www.hoot.test/odoo?k1=2&z=1&a=2");
    });
});

describe("History", () => {
    test("properly handles history.back and history.forward", async () => {
        redirect("/");
        on(routerBus, "ROUTE_CHANGE", () => expect.step("ROUTE_CHANGE"));
        createRouter();

        router.pushState({ k1: 1 });
        await tick();
        expect(browser.location.href).toBe("https://www.hoot.test/odoo?k1=1");

        router.pushState({ k2: 2 });
        await tick();
        expect(browser.location.href).toBe("https://www.hoot.test/odoo?k1=1&k2=2");

        router.pushState({ k3: 3 }, { replace: true });
        await tick();
        expect(browser.location.href).toBe("https://www.hoot.test/odoo?k3=3");

        browser.history.back(); // Click on back button
        await tick();
        expect(browser.location.href).toBe("https://www.hoot.test/odoo?k1=1&k2=2");

        router.pushState({ k4: 3 }, { replace: true }); // Click on a link
        await tick();
        expect(browser.location.href).toBe("https://www.hoot.test/odoo?k4=3");

        browser.history.back(); // Click on back button
        await tick();
        expect(browser.location.href).toBe("https://www.hoot.test/odoo?k1=1&k2=2");

        browser.history.forward(); // Click on forward button
        await tick();
        expect(browser.location.href).toBe("https://www.hoot.test/odoo?k4=3");

        expect.verifySteps(["ROUTE_CHANGE", "ROUTE_CHANGE", "ROUTE_CHANGE"]);
    });

    test("unserialized parts of action stack are preserved when going back/forward", async () => {
        redirect("/odoo");
        createRouter();
        expect(router.current).toEqual({});
        router.pushState({
            actionStack: [{ action: "some-path", displayName: "A cool display name" }],
        });
        await tick();
        expect(browser.location.href).toBe("https://www.hoot.test/odoo/some-path");
        expect(router.current).toEqual({
            actionStack: [{ action: "some-path", displayName: "A cool display name" }],
        });
        router.pushState({
            actionStack: [{ action: "other-path", displayName: "A different display name" }],
        });
        await tick();
        expect(browser.location.href).toBe("https://www.hoot.test/odoo/other-path");
        expect(router.current).toEqual({
            actionStack: [{ action: "other-path", displayName: "A different display name" }],
        });
        browser.history.back();
        await tick();
        expect(browser.location.href).toBe("https://www.hoot.test/odoo/some-path");
        expect(router.current).toEqual({
            actionStack: [{ action: "some-path", displayName: "A cool display name" }],
        });
        browser.history.forward();
        await tick();
        expect(browser.location.href).toBe("https://www.hoot.test/odoo/other-path");
        expect(router.current).toEqual({
            actionStack: [{ action: "other-path", displayName: "A different display name" }],
        });
    });
    test("properly handles history.back with hidden keys", async () => {
        redirect("/");
        on(routerBus, "ROUTE_CHANGE", () => expect.step("ROUTE_CHANGE"));
        createRouter();

        router.hideKeyFromUrl("k1");

        router.pushState({ k1: 1, k2: 2 });
        await tick();
        expect(router.current).toEqual({ k1: 1, k2: 2 });
        expect(browser.location.href).toBe("https://www.hoot.test/odoo?k2=2");

        router.pushState({ k3: 3 }, { replace: true }); // Click on a link
        await tick();
        expect(router.current).toEqual({ k3: 3 });
        expect(browser.location.href).toBe("https://www.hoot.test/odoo?k3=3");

        browser.history.back(); // Click on back button
        await tick();
        expect(router.current).toEqual({ k1: 1, k2: 2 });
        expect(browser.location.href).toBe("https://www.hoot.test/odoo?k2=2");

        expect.verifySteps(["ROUTE_CHANGE"]);
    });
});

describe("Scoped apps", () => {
    test("url location is changed to /odoo if the client is not used in a standalone scoped app", async () => {
        Object.assign(browser.location, { pathname: "/scoped_app/some-path" });
        createRouter();
        router.pushState({ app_name: "some_app", path: "scoped_app/some_path" });
        await tick();
        expect(browser.location.href).toBe("https://www.hoot.test/odoo/some-path?app_name=some_app&path=scoped_app%2Fsome_path");
    });
    test("url location is preserved as /scoped_app if the client is used in a standalone scoped app", async () => {
        mockMatchMedia({ ["display-mode"]: "standalone" });
        Object.assign(browser.location, { pathname: "/scoped_app/some-path" });
        createRouter();
        router.pushState({ app_name: "some_app", path: "scoped_app/some_path" });
        await tick();
        expect(browser.location.href).toBe("https://www.hoot.test/scoped_app/some-path?app_name=some_app&path=scoped_app%2Fsome_path");
    });
})

describe("Retrocompatibility", () => {
    test("parse an url with hash (key/values)", async () => {
        Object.assign(browser.location, { pathname: "/web" });
        browser.location.hash = "#a=114&k=c.e&f=1&g=91";
        createRouter();
        expect(browser.location.search).toBe("?a=114&k=c.e&f=1&g=91");
        expect(browser.location.hash).toBe("");
        expect(router.current).toEqual({ a: 114, k: "c.e", f: 1, g: 91 });
        expect(browser.location.pathname).toBe("/odoo");
    });

    test("parse an url with hash (key/values) and query string", async () => {
        Object.assign(browser.location, { pathname: "/web" });
        browser.location.hash = "#g=91";
        browser.location.search = "?a=114&t=c.e&f=1";
        createRouter();
        expect(browser.location.search).toBe("?a=114&t=c.e&f=1&g=91");
        expect(browser.location.hash).toBe("");
        expect(router.current).toEqual({ a: 114, t: "c.e", f: 1, g: 91 });
        expect(browser.location.pathname).toBe("/odoo");
    });

    test("parse an url with hash (anchor link)", async () => {
        redirect("/odoo#anchor");
        browser.location.hash = "#anchor";
        createRouter();
        expect(browser.location.search).toBe("");
        expect(browser.location.hash).toBe("#anchor");
        expect(browser.location.pathname).toBe("/odoo");
        expect(router.current).toEqual({});
    });

    test("parse an url with hash (anchor link) and query string", async () => {
        redirect("/odoo?a=114&g=c.e&f=1#anchor");
        browser.location.hash = "#anchor";
        browser.location.search = "?a=114&g=c.e&f=1";
        createRouter();
        expect(browser.location.search).toBe("?a=114&g=c.e&f=1");
        expect(browser.location.hash).toBe("#anchor");
        expect(router.current).toEqual({ a: 114, g: "c.e", f: 1 });
        expect(browser.location.pathname).toBe("/odoo");
    });
});

describe("internal links", () => {
    test("click on internal link does a loadState instead of a full reload", async () => {
        redirect("/odoo");
        createRouter({ onPushState: () => expect.step("pushState") });
        const fixture = getFixture();
        const link = document.createElement("a");
        link.href = "/odoo/some-action/2";
        fixture.appendChild(link);

        expect(router.current).toEqual({});

        let defaultPrevented;
        browser.addEventListener("click", (ev) => {
            expect.step("click");
            defaultPrevented = ev.defaultPrevented;
            ev.preventDefault();
        });
        await click("a");
        await tick();
        expect.verifySteps(["click"]);
        expect(router.current).toEqual({
            action: "some-action",
            actionStack: [
                {
                    action: "some-action",
                },
                {
                    action: "some-action",
                    resId: 2,
                },
            ],
            resId: 2,
        });
        expect(defaultPrevented).toBe(true);
    });

    test("click on internal link with children does a loadState instead of a full reload", async () => {
        redirect("/odoo");
        createRouter({ onPushState: () => expect.step("pushState") });
        const fixture = getFixture();
        const link = document.createElement("a");
        const span = document.createElement("span");
        link.appendChild(span);
        link.href = "/odoo/some-action/2";
        fixture.appendChild(link);

        expect(router.current).toEqual({});

        let defaultPrevented;
        browser.addEventListener("click", (ev) => {
            expect.step("click");
            defaultPrevented = ev.defaultPrevented;
            ev.preventDefault();
        });
        await click("span");
        await tick();
        expect.verifySteps(["click"]);
        expect(router.current).toEqual({
            action: "some-action",
            actionStack: [
                {
                    action: "some-action",
                },
                {
                    action: "some-action",
                    resId: 2,
                },
            ],
            resId: 2,
        });
        expect(defaultPrevented).toBe(true);
    });

    test("click on internal link with different protocol does a loadState", async () => {
        redirect("/odoo");
        createRouter({ onPushState: () => expect.step("pushState") });
        const fixture = getFixture();
        const link = document.createElement("a");
        link.href = "http://" + browser.location.host + "/odoo/some-action/2";
        fixture.appendChild(link);

        expect(router.current).toEqual({});
        expect(browser.location.protocol).not.toBe(link.protocol, {
            message:
                "should have different protocols between the current location and the clicked link",
        });

        let defaultPrevented;
        browser.addEventListener("click", (ev) => {
            expect.step("click");
            defaultPrevented = ev.defaultPrevented;
            ev.preventDefault();
        });
        await click("a");
        await tick();
        expect.verifySteps(["click"]);
        expect(router.current).toEqual({
            action: "some-action",
            actionStack: [
                {
                    action: "some-action",
                },
                {
                    action: "some-action",
                    resId: 2,
                },
            ],
            resId: 2,
        });
        expect(defaultPrevented).toBe(true);
    });

    test("click on internal link with hash (key/values)", async () => {
        redirect("/odoo");
        createRouter({
            onPushState: () => expect.step("pushState"),
            onReplaceState: () => expect.step("replaceState"),
        });
        const fixture = getFixture();
        const link = document.createElement("a");
        link.href = "/odoo/1/action-114/22";
        fixture.appendChild(link);

        expect(router.current).toEqual({});

        let defaultPrevented;
        browser.addEventListener("click", (ev) => {
            expect.step("click");
            defaultPrevented = ev.defaultPrevented;
            ev.preventDefault();
        });
        await click("a");
        await tick();
        expect.verifySteps(["click"]);
        expect(router.current).toEqual({
            action: 114,
            active_id: 1,
            actionStack: [
                {
                    active_id: 1,
                    action: 114,
                },
                {
                    active_id: 1,
                    resId: 22,
                    action: 114,
                },
            ],
            resId: 22,
        });
        expect(defaultPrevented).toBe(true);
    });

    test("click on internal link with hash (anchor)", async () => {
        redirect("/odoo");
        createRouter({
            onPushState: (_data, _unused, url) => {
                expect.step("pushState: " + url);
            },
            onReplaceState: () => expect.step("replaceState"),
        });
        const fixture = getFixture();
        const link = document.createElement("a");
        link.href = "/odoo/1/action-114/22#anchorId";
        fixture.appendChild(link);

        expect(router.current).toEqual({});

        let defaultPrevented;
        browser.addEventListener("click", (ev) => {
            expect.step("click");
            defaultPrevented = ev.defaultPrevented;
            ev.preventDefault();
        });
        await click("a");
        await tick();
        expect.verifySteps([
            "pushState: https://www.hoot.test/odoo/1/action-114/22#anchorId",
            "click",
        ]);
        expect(router.current).toEqual({
            action: 114,
            active_id: 1,
            actionStack: [
                {
                    active_id: 1,
                    action: 114,
                },
                {
                    active_id: 1,
                    resId: 22,
                    action: 114,
                },
            ],
            resId: 22,
        });
        expect(defaultPrevented).toBe(true);
    });

    test("click on internal link with target _blank doesn't do a loadState", async () => {
        redirect("/odoo");
        createRouter({ onPushState: () => expect.step("pushState") });
        const fixture = getFixture();
        const link = document.createElement("a");
        link.href = "/odoo/some-action/2";
        link.target = "_blank";
        fixture.appendChild(link);

        expect(router.current).toEqual({});

        let defaultPrevented;
        link.addEventListener("click", (ev) => {
            expect.step("click");
            defaultPrevented = ev.defaultPrevented;
            ev.preventDefault();
        });
        await click("a");
        await tick();
        expect.verifySteps(["click"]);
        expect(router.current).toEqual({});
        expect(defaultPrevented).toBe(false);
    });
});
