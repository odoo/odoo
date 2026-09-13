// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { MAX_ACTION_DEPTH } from "@web/webclient/actions/action_constants";
import { executeClientAction } from "@web/webclient/actions/action_executors/client";
import { NavigationTracker } from "@web/webclient/actions/navigation_token";

/** @param {Object} [overrides] */
function makeFakeAm(overrides = {}) {
    /** @type {Record<string, any[]>} */
    const calls = { updateUI: [], doAction: [], confirmLeave: [], actionInfo: [] };
    const am = {
        navigation: new NavigationTracker(),
        env: { isSmall: false, marker: "the-env" },
        confirmLeave: async (opts) => {
            calls.confirmLeave.push(opts);
            return true;
        },
        makeController: (params) => ({ jsId: "controller_1", ...params }),
        getActionInfo: (action, props) => {
            calls.actionInfo.push({ action, props });
            return { props };
        },
        updateUI: async (controller, options) => {
            calls.updateUI.push({ controller, options });
            return "updateUI-result";
        },
        doAction: async (action, options) => {
            calls.doAction.push({ action, options });
            return "doAction-result";
        },
        ...overrides,
    };
    am.__calls = calls;
    return am;
}

function defineClientAction(tag, entry) {
    registry.category("actions").add(tag, entry);
    return tag;
}

class SomeClientAction extends Component {
    static template = xml`<div/>`;
    static props = ["*"];
}

describe.current.tags("desktop");

test("a component entry is rendered through updateUI", async () => {
    const tag = defineClientAction("ce_plain", SomeClientAction);
    const am = makeFakeAm();
    const res = await executeClientAction(
        /** @type {any} */ ({ tag, type: "ir.actions.client" }),
        {},
        am,
    );
    expect(am.__calls.updateUI).toHaveLength(1);
    expect(am.__calls.updateUI[0].controller.Component).toBe(SomeClientAction);
    expect(res).toBe("updateUI-result");
});

test("a refused leave aborts before anything is rendered", async () => {
    const tag = defineClientAction("ce_refused", SomeClientAction);
    const am = makeFakeAm({ confirmLeave: async () => false });
    expect(await executeClientAction(/** @type {any} */ ({ tag }), {}, am)).toBe(
        undefined,
    );
    expect(am.__calls.updateUI).toEqual([]);
});

test("forceLeave is the only option forwarded to the leave check", async () => {
    const tag = defineClientAction("ce_force", SomeClientAction);
    const am = makeFakeAm();
    await executeClientAction(
        /** @type {any} */ ({ tag }),
        { forceLeave: true, props: { a: 1 } },
        am,
    );
    expect(am.__calls.confirmLeave).toEqual([{ forceLeave: true }]);
});

test("a dialog client action never asks permission to leave", async () => {
    const tag = defineClientAction("ce_dialog", SomeClientAction);
    const am = makeFakeAm();
    await executeClientAction(/** @type {any} */ ({ tag, target: "new" }), {}, am);
    expect(am.__calls.confirmLeave).toEqual([]);
});

test("opening in a new window never asks permission to leave", async () => {
    const tag = defineClientAction("ce_newwin", SomeClientAction);
    const am = makeFakeAm();
    await executeClientAction(/** @type {any} */ ({ tag }), { newWindow: true }, am);
    expect(am.__calls.confirmLeave).toEqual([]);
});

test("the registry entry's target overrides the action's", async () => {
    class TargetedAction extends SomeClientAction {}
    /** @type {any} */ (TargetedAction).target = "fullscreen";
    const tag = defineClientAction("ce_target", TargetedAction);
    const action = /** @type {any} */ ({ tag });
    const am = makeFakeAm();

    await executeClientAction(action, {}, am);

    expect(action.target).toBe("fullscreen");
});

test("the target override is skipped for a dialog", async () => {
    class TargetedAction extends SomeClientAction {}
    /** @type {any} */ (TargetedAction).target = "fullscreen";
    const tag = defineClientAction("ce_target_new", TargetedAction);
    const action = /** @type {any} */ ({ tag, target: "new" });
    await executeClientAction(action, {}, makeFakeAm());
    expect(action.target).toBe("new");
});

test("the registry entry's path is adopted only when the action has none", async () => {
    class PathedAction extends SomeClientAction {}
    /** @type {any} */ (PathedAction).path = "from-registry";
    const withoutPath = /** @type {any} */ ({
        tag: defineClientAction("ce_path", PathedAction),
    });
    await executeClientAction(withoutPath, {}, makeFakeAm());
    expect(withoutPath.path).toBe("from-registry");

    const withPath = /** @type {any} */ ({ tag: "ce_path", path: "explicit" });
    await executeClientAction(withPath, {}, makeFakeAm());
    expect(withPath.path).toBe("explicit");
});

test("extractProps output is merged under the caller's props", async () => {
    class PropsAction extends SomeClientAction {}
    /** @type {any} */ (PropsAction).extractProps = () => ({
        fromExtract: 1,
        shared: "extract",
    });
    const tag = defineClientAction("ce_props", PropsAction);
    const am = makeFakeAm();

    await executeClientAction(
        /** @type {any} */ ({ tag }),
        { props: { fromCaller: 2, shared: "caller" } },
        am,
    );

    expect(am.__calls.actionInfo[0].props).toEqual({
        fromExtract: 1,
        fromCaller: 2,
        shared: "caller",
    });
});

test("an entry without extractProps still gets the caller's props", async () => {
    const tag = defineClientAction("ce_noextract", SomeClientAction);
    const am = makeFakeAm();
    await executeClientAction(/** @type {any} */ ({ tag }), { props: { a: 1 } }, am);
    expect(am.__calls.actionInfo[0].props).toEqual({ a: 1 });
});

test("displayName falls back to the registry entry, then to empty string", async () => {
    class NamedAction extends SomeClientAction {}
    /** @type {any} */ (NamedAction).displayName = "Registry Name";
    const am = makeFakeAm();
    await executeClientAction(
        /** @type {any} */ ({ tag: defineClientAction("ce_named", NamedAction) }),
        {},
        am,
    );
    expect(am.__calls.updateUI[0].controller.displayName).toBe("Registry Name");

    const am2 = makeFakeAm();
    await executeClientAction(
        /** @type {any} */ ({
            tag: defineClientAction("ce_unnamed", SomeClientAction),
        }),
        {},
        am2,
    );
    expect(am2.__calls.updateUI[0].controller.displayName).toBe("");
});

test("a function entry runs for its side effects with (env, action, options)", async () => {
    const seen = [];
    const tag = defineClientAction("ce_fn", (env, action, options) => {
        seen.push({ env, action, options });
    });
    const am = makeFakeAm();
    const action = /** @type {any} */ ({ tag });

    const res = await executeClientAction(action, { clearBreadcrumbs: true }, am);

    expect(seen).toHaveLength(1);
    expect(seen[0].env.marker).toBe("the-env");
    expect(seen[0].action).toBe(action);
    expect(seen[0].options).toEqual({ clearBreadcrumbs: true });
    expect(res).toBe(undefined);
    expect(am.__calls.updateUI).toEqual([]);
    expect(am.__calls.doAction).toEqual([]);
});

test("a function entry never asks permission to leave", async () => {
    const tag = defineClientAction("ce_fn_noleave", () => {});
    const am = makeFakeAm();
    await executeClientAction(/** @type {any} */ ({ tag }), {}, am);
    expect(am.__calls.confirmLeave).toEqual([]);
});

test("a returned action is chained with an incremented depth", async () => {
    const next = { type: "ir.actions.act_window", res_model: "partner" };
    const tag = defineClientAction("ce_fn_chain", () => next);
    const am = makeFakeAm();

    const res = await executeClientAction(
        /** @type {any} */ ({ tag }),
        { _actionDepth: 2, onClose: () => {} },
        am,
    );

    expect(am.__calls.doAction).toHaveLength(1);
    expect(am.__calls.doAction[0].action).toBe(next);
    expect(am.__calls.doAction[0].options._actionDepth).toBe(3);
    expect(typeof am.__calls.doAction[0].options.onClose).toBe("function");
    expect(res).toBe("doAction-result");
});

test("an absent depth starts the chain at 1", async () => {
    const tag = defineClientAction("ce_fn_depth1", () => ({ type: "x" }));
    const am = makeFakeAm();
    await executeClientAction(/** @type {any} */ ({ tag }), {}, am);
    expect(am.__calls.doAction[0].options._actionDepth).toBe(1);
});

test("a cyclic client-action chain is stopped at MAX_ACTION_DEPTH", async () => {
    const tag = defineClientAction("ce_fn_runaway", () => ({ type: "x" }));
    const am = makeFakeAm();
    await expect(
        executeClientAction(
            /** @type {any} */ ({ tag }),
            { _actionDepth: MAX_ACTION_DEPTH },
            am,
        ),
    ).rejects.toThrow(/recursion limit exceeded/);
    expect(am.__calls.doAction).toEqual([]);
});

test("an async function entry is awaited before its result is chained", async () => {
    const tag = defineClientAction("ce_fn_async", async () => {
        await Promise.resolve();
        return { type: "ir.actions.act_window" };
    });
    const am = makeFakeAm();
    await executeClientAction(/** @type {any} */ ({ tag }), {}, am);
    expect(am.__calls.doAction).toHaveLength(1);
});
