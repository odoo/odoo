/** @odoo-module alias=@web/../tests/core/router_tests default=false */

import { browser } from "@web/core/browser/browser";
import {
    parseHash,
    parseSearchQuery,
    stateToUrl,
    urlToState,
    router,
    routerBus,
    startRouter,
} from "@web/core/browser/router";
import { nextTick, patchWithCleanup } from "../helpers/utils";
import { redirect } from "@web/core/utils/urls";

const _urlToState = (url) => urlToState(new URL(url, browser.location.origin));

async function createRouter(params = {}) {
    if (params.onPushState) {
        const originalPushState = browser.history.pushState;
        const onPushState = params.onPushState;
        delete params.onPushState;
        patchWithCleanup(browser, {
            history: Object.assign({}, browser.history, {
                pushState() {
                    originalPushState(...arguments);
                    onPushState(...arguments);
                },
            }),
        });
    }
    startRouter();
}

QUnit.module("Router");

QUnit.test("can parse an empty hash", (assert) => {
    assert.deepEqual(parseHash(""), {});
});

QUnit.test("can parse an single hash", (assert) => {
    assert.deepEqual(parseHash("#"), {});
});

QUnit.test("can parse a hash with a single key/value pair", (assert) => {
    const hash = "#action=114";
    assert.deepEqual(parseHash(hash), { action: 114 });
});

QUnit.test("can parse a hash with 2 key/value pairs", (assert) => {
    const hash = "#action=114&active_id=mail.box_inbox";
    assert.deepEqual(parseHash(hash), { action: 114, active_id: "mail.box_inbox" });
});

QUnit.test("a missing value is encoded as an empty string", (assert) => {
    const hash = "#action";
    assert.deepEqual(parseHash(hash), { action: "" });
});

QUnit.test("a missing value is encoded as an empty string -- 2", (assert) => {
    const hash = "#action=";
    assert.deepEqual(parseHash(hash), { action: "" });
});

QUnit.test("can parse a realistic hash", (assert) => {
    const hash = "#action=114&active_id=mail.box_inbox&cids=1&menu_id=91";
    const expected = {
        action: 114,
        active_id: "mail.box_inbox",
        cids: 1,
        menu_id: 91,
    };
    assert.deepEqual(parseHash(hash), expected);
});

QUnit.test("can parse an empty search", (assert) => {
    assert.deepEqual(parseSearchQuery(""), {});
});

QUnit.test("can parse an simple search with no value", (assert) => {
    assert.deepEqual(parseSearchQuery("?a"), { a: "" });
});

QUnit.test("can parse an simple search with a value", (assert) => {
    assert.deepEqual(parseSearchQuery("?a=1"), { a: 1 });
});

QUnit.test("can parse an search with 2 key/value pairs", (assert) => {
    assert.deepEqual(parseSearchQuery("?a=1&b=2"), { a: 1, b: 2 });
});

QUnit.test("can parse URI encoded strings", (assert) => {
    assert.deepEqual(parseSearchQuery("?space=this%20is"), { space: "this is" });
    assert.deepEqual(parseHash("#comma=that%2Cis"), { comma: "that,is" });
});

QUnit.module("Router: stateToUrl", () => {
    QUnit.test("encodes URI compatible strings", (assert) => {
        assert.strictEqual(stateToUrl({}), "/odoo");
        assert.strictEqual(stateToUrl({ a: "11", b: "summer wine" }), "/odoo?a=11&b=summer%20wine");
        assert.strictEqual(
            stateToUrl({ b: "2", c: "", e: "kloug,gloubi" }),
            "/odoo?b=2&c=&e=kloug%2Cgloubi"
        );
    });

    QUnit.test("backwards compatibility: no action stack, action encoded in path", (assert) => {
        assert.strictEqual(stateToUrl({}), "/odoo");
        // action
        assert.strictEqual(stateToUrl({ action: "some-path" }), "/odoo/some-path");
        assert.strictEqual(stateToUrl({ active_id: 5, action: "some-path" }), "/odoo/5/some-path");
        assert.strictEqual(stateToUrl({ action: "some-path", resId: 2 }), "/odoo/some-path/2");
        assert.strictEqual(
            stateToUrl({ active_id: 5, action: "some-path", resId: 2 }),
            "/odoo/5/some-path/2"
        );
        assert.strictEqual(
            stateToUrl({ active_id: 5, action: "some-path", resId: "new" }),
            "/odoo/5/some-path/new"
        );
        assert.strictEqual(
            stateToUrl({ action: 1, resId: 2 }),
            "/odoo/act-1/2",
            "action id instead of path/tag"
        );
        assert.strictEqual(
            stateToUrl({ action: "module.xml_id", resId: 2 }),
            "/odoo/act-module.xml_id/2",
            "action xml_id instead of path/tag"
        );
        // model
        assert.strictEqual(stateToUrl({ model: "some.model" }), "/odoo/some.model");
        assert.strictEqual(stateToUrl({ model: "some.model", resId: 2 }), "/odoo/some.model/2");
        assert.strictEqual(stateToUrl({ active_id: 5, model: "some.model" }), "/odoo/5/some.model");
        assert.strictEqual(
            stateToUrl({ active_id: 5, model: "some.model", resId: 2 }),
            "/odoo/5/some.model/2"
        );
        assert.strictEqual(
            stateToUrl({ active_id: 5, model: "some.model", resId: "new" }),
            "/odoo/5/some.model/new"
        );
        assert.strictEqual(
            stateToUrl({ active_id: 5, model: "some.model", view_type: "some_viewtype" }),
            "/odoo/5/some.model?view_type=some_viewtype"
        );
        // edge cases
        assert.strictEqual(
            stateToUrl({ active_id: 5, action: "some-path", resId: 2, some_key: "some_value" }),
            "/odoo/5/some-path/2?some_key=some_value",
            "pieces of state unrelated to actions are added as query string"
        );
        assert.strictEqual(
            stateToUrl({ active_id: 5, action: "some-path", model: "some.model", resId: 2 }),
            "/odoo/5/some-path/2",
            "action has priority on model"
        );
        assert.strictEqual(
            stateToUrl({ active_id: 5, model: "some.model", resId: 2, view_type: "list" }),
            "/odoo/5/some.model/2?view_type=list",
            "view_type and resId aren't incompatible"
            // Should they be? view_type will just be stripped by action_service
        );
    });

    QUnit.test("actionStack: one action", (assert) => {
        assert.strictEqual(stateToUrl({ actionStack: [] }), "/odoo");
        // action
        assert.strictEqual(
            stateToUrl({ actionStack: [{ action: "some-path" }] }),
            "/odoo/some-path"
        );
        assert.strictEqual(
            stateToUrl({ actionStack: [{ active_id: 5, action: "some-path" }] }),
            "/odoo/5/some-path"
        );
        assert.strictEqual(
            stateToUrl({ actionStack: [{ action: "some-path", resId: 2 }] }),
            "/odoo/some-path/2"
        );
        assert.strictEqual(
            stateToUrl({ actionStack: [{ active_id: 5, action: "some-path", resId: 2 }] }),
            "/odoo/5/some-path/2"
        );
        assert.strictEqual(
            stateToUrl({ actionStack: [{ active_id: 5, action: "some-path", resId: "new" }] }),
            "/odoo/5/some-path/new"
        );
        assert.strictEqual(
            stateToUrl({ actionStack: [{ action: 1, resId: 2 }] }),
            "/odoo/act-1/2",
            "numerical action id instead of path"
        );
        assert.strictEqual(
            stateToUrl({ actionStack: [{ action: "module.xml_id", resId: 2 }] }),
            "/odoo/act-module.xml_id/2",
            "action xml_id instead of path"
        );
        // model
        assert.strictEqual(
            stateToUrl({ actionStack: [{ model: "some.model" }] }),
            "/odoo/some.model"
        );
        assert.strictEqual(
            stateToUrl({ actionStack: [{ model: "some.model", resId: 2 }] }),
            "/odoo/some.model/2"
        );
        assert.strictEqual(
            stateToUrl({ actionStack: [{ active_id: 5, model: "some.model" }] }),
            "/odoo/5/some.model"
        );
        assert.strictEqual(
            stateToUrl({ actionStack: [{ active_id: 5, model: "some.model", resId: 2 }] }),
            "/odoo/5/some.model/2"
        );
        assert.strictEqual(
            stateToUrl({ actionStack: [{ active_id: 5, model: "some.model", resId: "new" }] }),
            "/odoo/5/some.model/new"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ active_id: 5, model: "some.model", view_type: "some_viewtype" }],
            }),
            "/odoo/5/some.model",
            "view_type is ignored in the action stack"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ active_id: 5, model: "some.model" }],
                view_type: "some_viewtype",
            }),
            "/odoo/5/some.model?view_type=some_viewtype",
            "view_type is added if it's on the state itself"
        );
        assert.strictEqual(
            stateToUrl({ actionStack: [{ active_id: 5, model: "model_no_dot", resId: 2 }] }),
            "/odoo/5/m-model_no_dot/2"
        );
        // edge cases
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { active_id: 5, action: "some-path", resId: 2, some_key: "some_value" },
                ],
            }),
            "/odoo/5/some-path/2",
            "pieces of state unrelated to actions are ignored in the actionStack"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ active_id: 5, action: "some-path", resId: 2 }],
                some_key: "some_value",
            }),
            "/odoo/5/some-path/2?some_key=some_value",
            "pieces of state unrelated to actions are added as query string even with actionStack"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ active_id: 5, action: "some-path", model: "some.model", resId: 2 }],
            }),
            "/odoo/5/some-path/2",
            "action has priority on model"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ active_id: 5, model: "some.model", resId: 2 }],
                view_type: "list",
            }),
            "/odoo/5/some.model/2?view_type=list",
            "view_type and resId aren't incompatible"
            // Should they be? view_type will just be stripped by action_service
        );
    });

    QUnit.test("actionStack: multiple actions", (assert) => {
        // different actions
        assert.strictEqual(
            stateToUrl({ actionStack: [{ action: "some-path" }, { action: "other-path" }] }),
            "/odoo/some-path/other-path"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ active_id: 5, action: "some-path" }, { action: "other-path" }],
            }),
            "/odoo/5/some-path/other-path"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ action: "some-path" }, { active_id: 7, action: "other-path" }],
            }),
            // On reload, this will generate a form view for the first action even though there was
            // originally none. This is probably fine.
            "/odoo/some-path/7/other-path"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ action: "some-path", resId: 2 }, { action: "other-path" }],
            }),
            // On reload, the second action will have an active_id even though it originally didn't
            // have one. This might be a problem?
            "/odoo/some-path/2/other-path"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ action: "some-path" }, { action: "other-path", resId: 2 }],
            }),
            // On reload, this will generate an action in the default multi-record view for the second
            // action. This is the desired behaviour.
            "/odoo/some-path/other-path/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { active_id: 5, action: "some-path", resId: 2 },
                    { action: "other-path" },
                ],
            }),
            "/odoo/5/some-path/2/other-path"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path" },
                    { active_id: 5, action: "other-path", resId: 2 },
                ],
            }),
            "/odoo/some-path/5/other-path/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path" },
                    { active_id: 5, action: "other-path", resId: "new" },
                ],
            }),
            "/odoo/some-path/5/other-path/new"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, action: "other-path" },
                ],
            }),
            "/odoo/some-path/5/other-path",
            "action with resId followed by action with same value as active_id is not duplicated"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, action: "other-path", resId: 2 },
                ],
            }),
            "/odoo/some-path/5/other-path/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ action: 1 }, { active_id: 5, action: 6, resId: 2 }],
            }),
            "/odoo/act-1/5/act-6/2",
            "numerical actions"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "module.xml_id" },
                    { active_id: 5, action: "module.other_xml_id", resId: 2 },
                ],
            }),
            "/odoo/act-module.xml_id/5/act-module.other_xml_id/2",
            "actions as xml_ids"
        );
        // same action twice
        assert.strictEqual(
            stateToUrl({ actionStack: [{ action: "some-path" }, { action: "some-path" }] }),
            "/odoo/some-path",
            "consolidates identical actions into one path segment"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ active_id: 5, action: "some-path" }, { action: "some-path" }],
            }),
            "/odoo/5/some-path/some-path",
            "doesn't consolidate the same action with different active_id"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 7 },
                    { active_id: 7, action: "some-path" },
                ],
            }),
            "/odoo/some-path/7/some-path",
            "doesn't remove multirecord action if it follows the same action in mono-record mode"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ action: "some-path", resId: 2 }, { action: "some-path" }],
            }),
            "/odoo/some-path/2/some-path"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { active_id: 7, action: "some-path", resId: 7 },
                    { active_id: 7, action: "some-path" },
                ],
            }),
            "/odoo/7/some-path/7/some-path",
            "doesn't remove multirecord action if it follows the same action in mono-record mode even if the active_id are the same"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ action: "some-path" }, { action: "some-path", resId: 2 }],
            }),
            "/odoo/some-path/2",
            "consolidates multi-record action with mono-record action"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { active_id: 5, action: "some-path" },
                    { active_id: 5, action: "some-path", resId: 2 },
                ],
            }),
            "/odoo/5/some-path/2",
            "consolidates multi-record action with mono-record action if they have the same active_id"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { active_id: 5, action: "some-path", resId: 2 },
                    { action: "some-path" },
                ],
            }),
            "/odoo/5/some-path/2/some-path"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path" },
                    { active_id: 5, action: "some-path", resId: 2 },
                ],
            }),
            "/odoo/some-path/5/some-path/2",
            "doesn't consolidate mono-record action into preceding multi-record action if active_id is not the same"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path" },
                    { active_id: 5, action: "some-path", resId: "new" },
                ],
            }),
            "/odoo/some-path/5/some-path/new"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, action: "some-path" },
                ],
            }),
            "/odoo/some-path/5/some-path",
            "action with resId followed by action with same value as active_id is not duplicated"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, action: "some-path", resId: 2 },
                ],
            }),
            "/odoo/some-path/5/some-path/2",
            "doesn't consolidate two mono-record actions"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { active_id: 5, action: "some-path", resId: 5 },
                    { active_id: 5, action: "some-path", resId: 2 },
                ],
            }),
            "/odoo/5/some-path/5/some-path/2",
            "doesn't consolidate two mono-record actions even with same active_id"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ action: 1 }, { active_id: 5, action: 1, resId: 2 }],
            }),
            "/odoo/act-1/5/act-1/2",
            "numerical actions"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "module.xml_id" },
                    { active_id: 5, action: "module.xml_id", resId: 2 },
                ],
            }),
            "/odoo/act-module.xml_id/5/act-module.xml_id/2",
            "actions as xml_ids"
        );
        // model
        assert.strictEqual(
            stateToUrl({ actionStack: [{ model: "some.model" }, { model: "other.model" }] }),
            "/odoo/some.model/other.model"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ active_id: 5, model: "some.model" }, { model: "other.model" }],
            }),
            "/odoo/5/some.model/other.model"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ model: "some.model" }, { active_id: 7, model: "other.model" }],
            }),
            "/odoo/some.model/7/other.model"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ model: "some.model", resId: 2 }, { model: "other.model" }],
            }),
            "/odoo/some.model/2/other.model"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ model: "some.model" }, { model: "other.model", resId: 2 }],
            }),
            "/odoo/some.model/other.model/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { active_id: 5, model: "some.model", resId: 2 },
                    { model: "other.model" },
                ],
            }),
            "/odoo/5/some.model/2/other.model"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { model: "some.model" },
                    { active_id: 5, model: "other.model", resId: 2 },
                ],
            }),
            "/odoo/some.model/5/other.model/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { model: "some.model" },
                    { active_id: 5, model: "other.model", resId: "new" },
                ],
            }),
            "/odoo/some.model/5/other.model/new"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { model: "some.model", resId: 5 },
                    { active_id: 5, model: "other.model" },
                ],
            }),
            "/odoo/some.model/5/other.model",
            "action with resId followed by action with same value as active_id is not duplicated"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { model: "some.model", resId: 5 },
                    { active_id: 5, model: "other.model", resId: 2 },
                ],
            }),
            "/odoo/some.model/5/other.model/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { model: "model_no_dot", resId: 5 },
                    { active_id: 5, model: "no_dot_model", resId: 2 },
                ],
            }),
            "/odoo/m-model_no_dot/5/m-no_dot_model/2"
        );
        // action + model
        assert.strictEqual(
            stateToUrl({ actionStack: [{ action: "some-path" }, { model: "some.model" }] }),
            "/odoo/some-path/some.model"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ active_id: 5, action: "some-path" }, { model: "some.model" }],
            }),
            "/odoo/5/some-path/some.model"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ action: "some-path" }, { active_id: 7, model: "some.model" }],
            }),
            "/odoo/some-path/7/some.model"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ action: "some-path", resId: 2 }, { model: "some.model" }],
            }),
            "/odoo/some-path/2/some.model"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ action: "some-path" }, { model: "some.model", resId: 2 }],
            }),
            "/odoo/some-path/some.model/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { active_id: 5, action: "some-path", resId: 2 },
                    { model: "some.model" },
                ],
            }),
            "/odoo/5/some-path/2/some.model"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path" },
                    { active_id: 5, model: "some.model", resId: 2 },
                ],
            }),
            "/odoo/some-path/5/some.model/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path" },
                    { active_id: 5, model: "some.model", resId: "new" },
                ],
            }),
            "/odoo/some-path/5/some.model/new"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, model: "some.model" },
                ],
            }),
            "/odoo/some-path/5/some.model",
            "action with resId followed by action with same value as active_id is not duplicated"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, model: "some.model", resId: 2 },
                ],
            }),
            "/odoo/some-path/5/some.model/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: 1, resId: 5 },
                    { active_id: 5, model: "model_no_dot", resId: 2 },
                ],
            }),
            "/odoo/act-1/5/m-model_no_dot/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "module.xml_id", resId: 5 },
                    { active_id: 5, model: "model_no_dot", resId: 2 },
                ],
            }),
            "/odoo/act-module.xml_id/5/m-model_no_dot/2"
        );
        // model + action
        assert.strictEqual(
            stateToUrl({ actionStack: [{ model: "some.model" }, { action: "other-path" }] }),
            "/odoo/some.model/other-path"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ active_id: 5, model: "some.model" }, { action: "other-path" }],
            }),
            "/odoo/5/some.model/other-path"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ model: "some.model" }, { active_id: 7, action: "other-path" }],
            }),
            "/odoo/some.model/7/other-path"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ model: "some.model", resId: 2 }, { action: "other-path" }],
            }),
            "/odoo/some.model/2/other-path"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [{ model: "some.model" }, { action: "other-path", resId: 2 }],
            }),
            "/odoo/some.model/other-path/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { active_id: 5, model: "some.model", resId: 2 },
                    { action: "other-path" },
                ],
            }),
            "/odoo/5/some.model/2/other-path"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { model: "some.model" },
                    { active_id: 5, action: "other-path", resId: 2 },
                ],
            }),
            "/odoo/some.model/5/other-path/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { model: "some.model" },
                    { active_id: 5, action: "other-path", resId: "new" },
                ],
            }),
            "/odoo/some.model/5/other-path/new"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { model: "some.model", resId: 5 },
                    { active_id: 5, action: "other-path" },
                ],
            }),
            "/odoo/some.model/5/other-path",
            "action with resId followed by action with same value as active_id is not duplicated"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { model: "some.model", resId: 5 },
                    { active_id: 5, action: "other-path", resId: 2 },
                ],
            }),
            "/odoo/some.model/5/other-path/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { model: "model_no_dot", resId: 5 },
                    { active_id: 5, action: 1, resId: 2 },
                ],
            }),
            "/odoo/m-model_no_dot/5/act-1/2"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { model: "model_no_dot", resId: 5 },
                    { active_id: 5, action: "module.xml_id", resId: 2 },
                ],
            }),
            "/odoo/m-model_no_dot/5/act-module.xml_id/2"
        );

        // edge cases
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5, some_key: "some_value" },
                    { active_id: 5, action: "other-path", resId: 2, other_key: "other_value" },
                ],
            }),
            "/odoo/some-path/5/other-path/2",
            "pieces of state unrelated to actions are ignored in the actionStack"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, action: "other-path", resId: 2 },
                ],
                some_key: "some_value",
            }),
            "/odoo/some-path/5/other-path/2?some_key=some_value",
            "pieces of state unrelated to actions are added as query string even with actionStack"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path", model: "some.model", resId: 5 },
                    { active_id: 5, action: "other-path", model: "other.model", resId: 2 },
                ],
            }),
            "/odoo/some-path/5/other-path/2",
            "action has priority on model"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 5 },
                    { active_id: 5, model: "some.model", resId: 2 },
                ],
                view_type: "list",
            }),
            "/odoo/some-path/5/some.model/2?view_type=list",
            "view_type and resId aren't incompatible"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "some-path", resId: 2 },
                    { active_id: 5, action: "other-path" },
                ],
            }),
            "/odoo/some-path/2/5/other-path",
            "action with resId followed by action with different active_id gets both ids in a row"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { model: "some.model", resId: 2 },
                    { active_id: 5, model: "other.model" },
                ],
            }),
            "/odoo/some.model/2/5/other.model",
            "action with resId followed by action with different active_id gets both ids in a row"
        );
        assert.strictEqual(
            stateToUrl({
                actionStack: [
                    { action: "other-path", resId: 5 },
                    { active_id: 5, action: "some-path" },
                    { active_id: 5, action: "some-path", resId: 2 },
                ],
            }),
            "/odoo/other-path/5/some-path/2",
            "active_id of last action is correctly removed even if previous action's active id is also removed because of the preceding resId"
        );
    });
});

QUnit.module("Router: urlToState", () => {
    QUnit.test("deserialize queryString", (assert) => {
        assert.deepEqual(_urlToState("/odoo?a=11&g=summer%20wine"), {
            a: 11,
            g: "summer wine",
        });
        assert.deepEqual(_urlToState("/odoo?g=2&c=&e=kloug%2Cgloubi"), {
            g: 2,
            c: "",
            e: "kloug,gloubi",
        });
    });

    QUnit.test("deserialize action in legacy url form", (assert) => {
        assert.deepEqual(
            _urlToState("/web#id=5&action=1&model=some.model&view_type=form&menu_id=137&cids=1"),
            {
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
            }
        );

        assert.deepEqual(
            _urlToState("/web#id=5&model=some.model&view_type=form&menu_id=137&cids=1"),
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
            "no action"
        );
    });

    QUnit.test("deserialize single action", (assert) => {
        assert.deepEqual(_urlToState(""), {});
        assert.deepEqual(_urlToState("/odoo"), {});
        // action
        assert.deepEqual(_urlToState("/odoo/some-path"), {
            action: "some-path",
            actionStack: [{ action: "some-path" }],
        });
        assert.deepEqual(_urlToState("/odoo/5/some-path"), {
            active_id: 5,
            action: "some-path",
            actionStack: [{ active_id: 5, action: "some-path" }],
        });
        assert.deepEqual(
            _urlToState("/odoo/some-path/2"),
            {
                action: "some-path",
                resId: 2,
                actionStack: [{ action: "some-path" }, { action: "some-path", resId: 2 }],
            },
            "two actions are created for action with resId"
        );
        assert.deepEqual(
            _urlToState("/odoo/some-path/new"),
            {
                action: "some-path",
                resId: "new",
                actionStack: [{ action: "some-path" }, { action: "some-path", resId: "new" }],
            },
            "new record"
        );
        assert.deepEqual(_urlToState("/odoo/5/some-path/2"), {
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
        assert.deepEqual(_urlToState("/odoo/act-1/2"), {
            action: 1,
            resId: 2,
            actionStack: [{ action: 1 }, { action: 1, resId: 2 }],
        });
        assert.deepEqual(_urlToState("/odoo/act-module.xml_id/2"), {
            action: "module.xml_id",
            resId: 2,
            actionStack: [{ action: "module.xml_id" }, { action: "module.xml_id", resId: 2 }],
        });
        // model
        assert.deepEqual(_urlToState("/odoo/some.model"), {
            model: "some.model",
            actionStack: [{ model: "some.model" }],
        });
        assert.deepEqual(
            _urlToState("/odoo/some.model/2"),
            {
                model: "some.model",
                resId: 2,
                actionStack: [{ model: "some.model", resId: 2 }],
            },
            "single action is created for model with resId"
        );
        assert.deepEqual(
            _urlToState("/odoo/some.model/new"),
            {
                model: "some.model",
                resId: "new",
                actionStack: [{ model: "some.model", resId: "new" }],
            },
            "new record"
        );
        assert.deepEqual(_urlToState("/odoo/5/some.model"), {
            active_id: 5,
            model: "some.model",
            actionStack: [{ active_id: 5, model: "some.model" }],
        });
        assert.deepEqual(_urlToState("/odoo/5/some.model/2"), {
            active_id: 5,
            model: "some.model",
            resId: 2,
            actionStack: [{ active_id: 5, model: "some.model", resId: 2 }],
        });
        assert.deepEqual(
            _urlToState("/odoo/5/some.model?view_type=some_viewtype"),
            {
                active_id: 5,
                model: "some.model",
                view_type: "some_viewtype",
                actionStack: [{ active_id: 5, model: "some.model" }],
            },
            "view_type doesn't end up in the actionStack"
        );
        assert.deepEqual(_urlToState("/odoo/m-model_no_dot/2"), {
            model: "model_no_dot",
            resId: 2,
            actionStack: [{ model: "model_no_dot", resId: 2 }],
        });
        // edge cases
        assert.deepEqual(
            _urlToState("/odoo/5/some-path/2?some_key=some_value"),
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
            "pieces of state unrelated to actions end up on the state but not in the actionStack"
        );
        assert.deepEqual(
            _urlToState("/odoo/5/some.model/2?view_type=list"),
            {
                active_id: 5,
                model: "some.model",
                resId: 2,
                view_type: "list",
                actionStack: [{ active_id: 5, model: "some.model", resId: 2 }],
            },
            "view_type and resId aren't incompatible"
        );
    });

    QUnit.test("deserialize multiple actions", (assert) => {
        // action
        assert.deepEqual(_urlToState("/odoo/some-path/other-path"), {
            action: "other-path",
            actionStack: [{ action: "some-path" }, { action: "other-path" }],
        });
        assert.deepEqual(_urlToState("/odoo/5/some-path/other-path"), {
            action: "other-path",
            actionStack: [{ active_id: 5, action: "some-path" }, { action: "other-path" }],
        });
        assert.deepEqual(_urlToState("/odoo/some-path/2/other-path"), {
            action: "other-path",
            active_id: 2,
            actionStack: [
                { action: "some-path" },
                { action: "some-path", resId: 2 },
                { active_id: 2, action: "other-path" },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/some-path/other-path/2"), {
            action: "other-path",
            resId: 2,
            actionStack: [
                { action: "some-path" },
                { action: "other-path" },
                { action: "other-path", resId: 2 },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/5/some-path/2/other-path"), {
            action: "other-path",
            active_id: 2,
            actionStack: [
                { active_id: 5, action: "some-path" },
                { active_id: 5, action: "some-path", resId: 2 },
                { active_id: 2, action: "other-path" },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/some-path/5/other-path/2"), {
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
        assert.deepEqual(_urlToState("/odoo/some-path/5/other-path/new"), {
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
        assert.deepEqual(_urlToState("/odoo/act-1/5/act-6/2"), {
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
        assert.deepEqual(_urlToState("/odoo/act-module.xml_id/5/act-module.other_xml_id/2"), {
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
        assert.deepEqual(
            _urlToState("/odoo/some.model/other.model"),
            {
                model: "other.model",
                actionStack: [{ model: "other.model" }],
            },
            "model not followed by resId doesn't generate an action unless it's the last one"
        );
        assert.deepEqual(
            _urlToState("/odoo/5/some.model/other.model"),
            {
                model: "other.model",
                actionStack: [{ model: "other.model" }],
            },
            "model not followed by resId doesn't generate an action unless it's the last one, even with an active_id"
        );
        assert.deepEqual(_urlToState("/odoo/some.model/7/other.model"), {
            active_id: 7,
            model: "other.model",
            actionStack: [
                { model: "some.model", resId: 7 },
                { active_id: 7, model: "other.model" },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/some.model/other.model/2"), {
            model: "other.model",
            resId: 2,
            actionStack: [{ model: "other.model", resId: 2 }],
        });
        assert.deepEqual(_urlToState("/odoo/5/some.model/2/other.model"), {
            active_id: 2,
            model: "other.model",
            actionStack: [
                { active_id: 5, model: "some.model", resId: 2 },
                { active_id: 2, model: "other.model" },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/some.model/5/other.model/2"), {
            active_id: 5,
            model: "other.model",
            resId: 2,
            actionStack: [
                { model: "some.model", resId: 5 },
                { active_id: 5, model: "other.model", resId: 2 },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/some.model/5/other.model/new"), {
            active_id: 5,
            model: "other.model",
            resId: "new",
            actionStack: [
                { model: "some.model", resId: 5 },
                { active_id: 5, model: "other.model", resId: "new" },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/m-model_no_dot/5/m-no_dot_model/2"), {
            active_id: 5,
            model: "no_dot_model",
            resId: 2,
            actionStack: [
                { model: "model_no_dot", resId: 5 },
                { active_id: 5, model: "no_dot_model", resId: 2 },
            ],
        });
        // action + model
        assert.deepEqual(_urlToState("/odoo/some-path/some.model"), {
            model: "some.model",
            actionStack: [{ action: "some-path" }, { model: "some.model" }],
        });
        assert.deepEqual(_urlToState("/odoo/5/some-path/some.model"), {
            model: "some.model",
            actionStack: [{ active_id: 5, action: "some-path" }, { model: "some.model" }],
        });
        assert.deepEqual(_urlToState("/odoo/some-path/7/some.model"), {
            active_id: 7,
            model: "some.model",
            actionStack: [
                { action: "some-path" },
                { action: "some-path", resId: 7 },
                { active_id: 7, model: "some.model" },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/some-path/some.model/2"), {
            model: "some.model",
            resId: 2,
            actionStack: [{ action: "some-path" }, { model: "some.model", resId: 2 }],
        });
        assert.deepEqual(_urlToState("/odoo/5/some-path/2/some.model"), {
            active_id: 2,
            model: "some.model",
            actionStack: [
                { active_id: 5, action: "some-path" },
                { active_id: 5, action: "some-path", resId: 2 },
                { active_id: 2, model: "some.model" },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/some-path/5/some.model/2"), {
            active_id: 5,
            model: "some.model",
            resId: 2,
            actionStack: [
                { action: "some-path" },
                { action: "some-path", resId: 5 },
                { active_id: 5, model: "some.model", resId: 2 },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/some-path/5/some.model/new"), {
            active_id: 5,
            model: "some.model",
            resId: "new",
            actionStack: [
                { action: "some-path" },
                { action: "some-path", resId: 5 },
                { active_id: 5, model: "some.model", resId: "new" },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/act-1/5/m-model_no_dot/2"), {
            active_id: 5,
            model: "model_no_dot",
            resId: 2,
            actionStack: [
                { action: 1 },
                { action: 1, resId: 5 },
                { active_id: 5, model: "model_no_dot", resId: 2 },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/act-module.xml_id/5/m-model_no_dot/2"), {
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
        assert.deepEqual(_urlToState("/odoo/some.model/other-path"), {
            action: "other-path",
            actionStack: [{ action: "other-path" }],
        });
        assert.deepEqual(_urlToState("/odoo/5/some.model/other-path"), {
            action: "other-path",
            actionStack: [{ action: "other-path" }],
        });
        assert.deepEqual(_urlToState("/odoo/some.model/2/other-path"), {
            active_id: 2,
            action: "other-path",
            actionStack: [
                { model: "some.model", resId: 2 },
                { active_id: 2, action: "other-path" },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/some.model/other-path/2"), {
            action: "other-path",
            resId: 2,
            actionStack: [{ action: "other-path" }, { action: "other-path", resId: 2 }],
        });
        assert.deepEqual(_urlToState("/odoo/5/some.model/2/other-path"), {
            active_id: 2,
            action: "other-path",
            actionStack: [
                { active_id: 5, model: "some.model", resId: 2 },
                { active_id: 2, action: "other-path" },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/some.model/5/other-path/2"), {
            active_id: 5,
            action: "other-path",
            resId: 2,
            actionStack: [
                { model: "some.model", resId: 5 },
                { active_id: 5, action: "other-path" },
                { active_id: 5, action: "other-path", resId: 2 },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/some.model/5/other-path/new"), {
            active_id: 5,
            action: "other-path",
            resId: "new",
            actionStack: [
                { model: "some.model", resId: 5 },
                { active_id: 5, action: "other-path" },
                { active_id: 5, action: "other-path", resId: "new" },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/m-model_no_dot/5/act-1/2"), {
            active_id: 5,
            action: 1,
            resId: 2,
            actionStack: [
                { model: "model_no_dot", resId: 5 },
                { active_id: 5, action: 1 },
                { active_id: 5, action: 1, resId: 2 },
            ],
        });
        assert.deepEqual(_urlToState("/odoo/m-model_no_dot/5/act-module.xml_id/2"), {
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
        assert.deepEqual(_urlToState("/odoo/some-path/5/other-path/2?some_key=some_value"), {
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
        assert.deepEqual(
            _urlToState("/odoo/some-path/5/some.model?view_type=list"),
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
            "view_type doesn't end up in the actionStack"
        );
        assert.deepEqual(
            _urlToState("/odoo/some-path/5/some.model/2?view_type=list"),
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
            "view_type and resId aren't incompatible"
        );
        assert.deepEqual(
            _urlToState("/odoo/some-path/2/5/other-path"),
            {
                active_id: 5,
                action: "other-path",
                actionStack: [
                    { action: "some-path" },
                    { action: "some-path", resId: 2 },
                    { active_id: 5, action: "other-path" },
                ],
            },
            "resId immediately following active_id: action"
        );
        assert.deepEqual(
            _urlToState("/odoo/some.model/2/5/other.model"),
            {
                active_id: 5,
                model: "other.model",
                actionStack: [
                    { model: "some.model", resId: 2 },
                    { active_id: 5, model: "other.model" },
                ],
            },
            "resId immediately following active_id: model"
        );
    });
});

QUnit.module("Router: Push state");

QUnit.test("can push in same timeout", async (assert) => {
    await createRouter();

    assert.deepEqual(router.current, {});

    router.pushState({ k1: 2 });
    assert.deepEqual(router.current, {});

    router.pushState({ k1: 3 });
    assert.deepEqual(router.current, {});
    await nextTick();
    assert.deepEqual(router.current, { k1: 3 });
});

QUnit.test("can lock keys", async (assert) => {
    await createRouter();

    router.addLockedKey(["k1"]);

    router.replaceState({ k1: 2 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 2 });

    router.replaceState({ k1: 3 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 3 });

    router.replaceState({ k2: 4 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 3, k2: 4 });

    router.replaceState({ k1: 4 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 4, k2: 4 });
});

QUnit.test("can re-lock keys in same final call", async (assert) => {
    await createRouter();

    router.addLockedKey(["k1"]);

    router.pushState({ k1: 2 });
    await nextTick();
    router.pushState({ k2: 1 });
    router.pushState({ k1: 4 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 4, k2: 1 });
});

QUnit.test("can replace search state", async (assert) => {
    await createRouter();

    router.pushState({ k1: 2 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 2 });

    router.pushState({ k2: 3 }, { replace: true });
    await nextTick();
    assert.deepEqual(router.current, { k2: 3 });
});

QUnit.test("can replace search state with locked keys", async (assert) => {
    await createRouter();

    router.addLockedKey("k1");

    router.pushState({ k1: 2 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 2 });

    router.pushState({ k2: 3 }, { replace: true });
    await nextTick();
    assert.deepEqual(router.current, { k1: 2, k2: 3 });
});

QUnit.test("can merge hash", async (assert) => {
    await createRouter();

    router.pushState({ k1: 2 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 2 });

    router.pushState({ k2: 3 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 2, k2: 3 });
});

QUnit.test("undefined keys are not pushed", async (assert) => {
    const onPushState = () => assert.step("pushed state");
    await createRouter({ onPushState });

    router.pushState({ k1: undefined });
    await nextTick();
    assert.verifySteps([]);
    assert.deepEqual(router.current, {});
});

QUnit.test("undefined keys destroy previous non locked keys", async (assert) => {
    await createRouter();

    router.pushState({ k1: 1 });
    await nextTick();
    assert.deepEqual(router.current, { k1: 1 });

    router.pushState({ k1: undefined });
    await nextTick();
    assert.deepEqual(router.current, {});
});

QUnit.test("do not re-push when hash is same", async (assert) => {
    const onPushState = () => assert.step("pushed state");
    await createRouter({ onPushState });

    router.pushState({ k1: 1, k2: 2 });
    await nextTick();
    assert.verifySteps(["pushed state"]);

    router.pushState({ k2: 2, k1: 1 });
    await nextTick();
    assert.verifySteps([]);
});

QUnit.test("do not re-push when hash is same (with integers as strings)", async (assert) => {
    const onPushState = () => assert.step("pushed state");
    await createRouter({ onPushState });

    router.pushState({ k1: 1, k2: "2" });
    await nextTick();
    assert.verifySteps(["pushed state"]);

    router.pushState({ k2: 2, k1: "1" });
    await nextTick();
    assert.verifySteps([]);
});

QUnit.test("pushState adds action-related keys to last entry in actionStack", async (assert) => {
    await createRouter();

    router.pushState({ action: 1, resId: 2, actionStack: [{ action: 1, resId: 2 }] });
    await nextTick();
    assert.deepEqual(router.current, {
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
    await nextTick();
    assert.deepEqual(router.current, {
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

QUnit.test("test the help utils history.back and history.forward", async (assert) => {
    patchWithCleanup(browser.location, {
        origin: "http://example.com",
    });
    redirect("/");
    routerBus.addEventListener("ROUTE_CHANGE", () => assert.step("ROUTE_CHANGE"));
    await createRouter();

    router.pushState({ k1: 1 });
    await nextTick();
    assert.deepEqual(browser.location.href, "http://example.com/odoo?k1=1");

    router.pushState({ k2: 2 });
    await nextTick();
    assert.deepEqual(browser.location.href, "http://example.com/odoo?k1=1&k2=2");

    router.pushState({ k3: 3 }, { replace: true });
    await nextTick();
    assert.deepEqual(browser.location.href, "http://example.com/odoo?k3=3");

    browser.history.back(); // Click on back button
    await nextTick();
    assert.deepEqual(browser.location.href, "http://example.com/odoo?k1=1&k2=2");

    router.pushState({ k4: 3 }, { replace: true }); // Click on a link
    await nextTick();
    assert.deepEqual(browser.location.href, "http://example.com/odoo?k4=3");

    browser.history.back(); // Click on back button
    await nextTick();
    assert.deepEqual(browser.location.href, "http://example.com/odoo?k1=1&k2=2");

    browser.history.forward(); // Click on forward button
    await nextTick();
    assert.deepEqual(browser.location.href, "http://example.com/odoo?k4=3");

    assert.verifySteps(["ROUTE_CHANGE", "ROUTE_CHANGE", "ROUTE_CHANGE"]);
});

QUnit.test(
    "unserialized parts of action stack are preserved when going back/forward",
    async (assert) => {
        patchWithCleanup(browser.location, {
            origin: "http://example.com",
        });
        redirect("/odoo");
        await createRouter();
        assert.deepEqual(router.current, {});
        router.pushState({
            actionStack: [{ action: "some-path", displayName: "A cool display name" }],
        });
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo/some-path");
        assert.deepEqual(router.current, {
            actionStack: [{ action: "some-path", displayName: "A cool display name" }],
        });
        router.pushState({
            actionStack: [{ action: "other-path", displayName: "A different display name" }],
        });
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo/other-path");
        assert.deepEqual(router.current, {
            actionStack: [{ action: "other-path", displayName: "A different display name" }],
        });
        browser.history.back();
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo/some-path");
        assert.deepEqual(router.current, {
            actionStack: [{ action: "some-path", displayName: "A cool display name" }],
        });
        browser.history.forward();
        await nextTick();
        assert.strictEqual(browser.location.href, "http://example.com/odoo/other-path");
        assert.deepEqual(router.current, {
            actionStack: [{ action: "other-path", displayName: "A different display name" }],
        });
    }
);

QUnit.module("Router: Retrocompatibility");

QUnit.test("parse an url with hash (key/values)", async (assert) => {
    Object.assign(browser.location, { pathname: "/web" });
    browser.location.hash = "#a=114&k=c.e&f=1&g=91";
    await createRouter();
    assert.strictEqual(browser.location.search, "?a=114&k=c.e&f=1&g=91");
    assert.strictEqual(browser.location.hash, "");
    assert.deepEqual(router.current, { a: 114, k: "c.e", f: 1, g: 91 });
    assert.strictEqual(browser.location.pathname, "/odoo");
});

QUnit.test("parse an url with hash (key/values) and query string", async (assert) => {
    Object.assign(browser.location, { pathname: "/web" });
    browser.location.hash = "#g=91";
    browser.location.search = "?a=114&t=c.e&f=1";
    await createRouter();
    assert.strictEqual(browser.location.search, "?a=114&t=c.e&f=1&g=91");
    assert.strictEqual(browser.location.hash, "");
    assert.deepEqual(router.current, { a: 114, t: "c.e", f: 1, g: 91 });
    assert.strictEqual(browser.location.pathname, "/odoo");
});

QUnit.test("parse an url with hash (anchor link)", async (assert) => {
    redirect("/odoo#anchor");
    browser.location.hash = "#anchor";
    await createRouter();
    assert.strictEqual(browser.location.search, "");
    assert.strictEqual(browser.location.hash, "#anchor");
    assert.strictEqual(browser.location.pathname, "/odoo");
    assert.deepEqual(router.current, {});
});

QUnit.test("parse an url with hash (anchor link) and query string", async (assert) => {
    redirect("/odoo?a=114&g=c.e&f=1#anchor");
    browser.location.hash = "#anchor";
    browser.location.search = "?a=114&g=c.e&f=1";
    await createRouter();
    assert.strictEqual(browser.location.search, "?a=114&g=c.e&f=1");
    assert.strictEqual(browser.location.hash, "#anchor");
    assert.deepEqual(router.current, { a: 114, g: "c.e", f: 1 });
    assert.strictEqual(browser.location.pathname, "/odoo");
});
