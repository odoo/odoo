// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineModels,
    fields,
    models,
    mountWithSearch,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { makeLogger } from "@web/core/debug/debug_logger";
import { Deferred } from "@web/core/utils/concurrency";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import {
    EmbeddedActions,
    EmbeddedActionsConfigHandler,
} from "@web/search/embedded_actions_bar/embedded_actions";
import { EmbeddedActionsDropdown } from "@web/search/embedded_actions_bar/embedded_actions_dropdown";

/**
 * @param {Object} orm
 * @param {Function} setEmbeddedActionsConfig
 */
function makeSelf(orm, setEmbeddedActionsConfig) {
    return {
        embeddedInfos: {
            visibleEmbeddedActions: [7, 8],
            embeddedActions: [{ id: 7 }, { id: 8 }],
            currentEmbeddedAction: { id: 8 },
        },
        orm,
        configHandler: { setEmbeddedActionsConfig },
    };
}

/**
 * @param {Object} [params]
 * @param {Object} [params.orm]
 * @param {Object} [params.notification]
 * @param {Object} [params.initialConfig]
 */
function makeConfigHandler({ orm, notification, initialConfig } = {}) {
    const handler = Object.create(EmbeddedActionsConfigHandler.prototype);
    handler.parentActionId = 1;
    handler.currentActiveId = false;
    handler.embeddedActionsKey = "1+";
    handler.embeddedActionsConfig = initialConfig || {};
    handler.orm = orm || { call: async () => true };
    handler.notification = notification || { add: () => {} };
    handler._writeQueue = Promise.resolve();
    return handler;
}

describe("EmbeddedActions.removeAction", () => {
    test("server refusal leaves the tab and settings intact", async () => {
        let settingsCalls = 0;
        const self = makeSelf(
            {
                unlink: async () => {
                    throw new Error("Access Denied");
                },
            },
            async () => {
                settingsCalls++;
            },
        );

        await expect(
            EmbeddedActions.prototype.removeAction.call(self, {
                id: 7,
                parent_action_id: 1,
                name: "Action 7",
                parent_res_model: "res.partner",
                action_id: 7,
            }),
        ).rejects.toThrow();

        expect(self.embeddedInfos.visibleEmbeddedActions).toEqual([7, 8]);
        expect(self.embeddedInfos.embeddedActions.map((a) => a.id)).toEqual([7, 8]);
        expect(settingsCalls).toBe(0);
    });

    test("successful unlink removes the tab and persists settings once", async () => {
        /** @type {any} */
        let savedConfig = null;
        let settingsCalls = 0;
        const self = makeSelf(
            { unlink: async () => true },
            async (/** @type {any} */ config) => {
                settingsCalls++;
                savedConfig = config;
                return true;
            },
        );

        await EmbeddedActions.prototype.removeAction.call(self, {
            id: 7,
            parent_action_id: 1,
            name: "Action 7",
            parent_res_model: "res.partner",
            action_id: 7,
        });

        expect(self.embeddedInfos.visibleEmbeddedActions).toEqual([8]);
        expect(self.embeddedInfos.embeddedActions.map((a) => a.id)).toEqual([8]);
        expect(settingsCalls).toBe(1);
        expect(savedConfig).toEqual({
            embedded_actions_visibility: [8],
            embedded_actions_order: [8],
        });
    });
});

describe("EmbeddedActionsConfigHandler.setEmbeddedActionsConfig", () => {
    test("stores a deep copy: later caller mutations do not reach the cache", async () => {
        const handler = makeConfigHandler();
        const visibility = [7];

        await handler.setEmbeddedActionsConfig({
            embedded_actions_visibility: visibility,
        });
        visibility.push(8);

        expect(handler.getEmbeddedActionsConfig("embedded_actions_visibility")).toEqual(
            [7],
        );
    });

    test("RPC failure with an existing config reverts the array payload", async () => {
        /** @type {any[]} */
        const notifications = [];
        const handler = makeConfigHandler({
            orm: {
                call: async () => {
                    throw new Error("boom");
                },
            },
            notification: {
                add: (/** @type {any} */ _msg, /** @type {any} */ opts) =>
                    notifications.push(opts.type),
            },
            initialConfig: { "1+": { embedded_actions_visibility: [7, 8] } },
        });

        const saved = await handler.setEmbeddedActionsConfig({
            embedded_actions_visibility: [7],
        });

        expect(saved).toBe(false);
        expect(handler.getEmbeddedActionsConfig("embedded_actions_visibility")).toEqual(
            [7, 8],
        );
        expect(notifications).toEqual(["danger"]);
    });

    test("RPC failure without an existing config deletes the entry", async () => {
        const handler = makeConfigHandler({
            orm: {
                call: async () => {
                    throw new Error("boom");
                },
            },
        });

        const saved = await handler.setEmbeddedActionsConfig({
            embedded_visibility: true,
        });

        expect(saved).toBe(false);
        expect(handler.hasEmbeddedActionsConfig()).toBe(false);
    });

    test("overlapping writes: an earlier failure does not wipe a later success", async () => {
        let call = 0;
        const handler = makeConfigHandler({
            orm: {
                call: async () => {
                    call++;
                    if (call === 1) {
                        throw new Error("boom");
                    }
                    return true;
                },
            },
        });

        const first = handler.setEmbeddedActionsConfig({
            embedded_actions_visibility: [7],
        });
        const second = handler.setEmbeddedActionsConfig({
            embedded_actions_visibility: [7, 8],
        });
        const [firstSaved, secondSaved] = await Promise.all([first, second]);

        expect(firstSaved).toBe(false);
        expect(secondSaved).toBe(true);
        expect(handler.getEmbeddedActionsConfig("embedded_actions_visibility")).toEqual(
            [7, 8],
        );
    });

    test("success returns true and merges into the existing entry", async () => {
        const handler = makeConfigHandler({
            initialConfig: { "1+": { embedded_visibility: false } },
        });

        const saved = await handler.setEmbeddedActionsConfig({
            embedded_actions_order: [7, 8],
        });

        expect(saved).toBe(true);
        expect(handler.getEmbeddedActionsConfig("embedded_visibility")).toBe(false);
        expect(handler.getEmbeddedActionsConfig("embedded_actions_order")).toEqual([
            7, 8,
        ]);
    });
});

test("deletion preserves a reorder and visibility change completed while unlink waited", async () => {
    const pendingUnlink = new Deferred();
    const self = {
        embeddedInfos: {
            embeddedActions: [{ id: 7 }, { id: 8 }, { id: 9 }],
            visibleEmbeddedActions: [7, 8],
            currentEmbeddedAction: { id: 8 },
        },
        orm: { unlink: () => pendingUnlink },
        configHandler: { setEmbeddedActionsConfig: async () => true },
        sortActions: EmbeddedActions.prototype.sortActions,
    };
    const deletion = EmbeddedActions.prototype.removeAction.call(self, {
        id: 7,
        name: "Deleted action",
        parent_action_id: 1,
        parent_res_model: "foo",
        action_id: 2,
    });
    const element = document.createElement("button");
    element.dataset.embeddedIndex = "2";
    await EmbeddedActions.prototype.reorderFromDrop.call(self, { element });
    await EmbeddedActions.prototype.toggleActionVisibility.call(self, 9);
    pendingUnlink.resolve();
    await deletion;
    makeLogger("web.search.correctness").logic("deletion-after-layout-change", () => ({
        state: self.embeddedInfos,
    }));
    expect(self.embeddedInfos.embeddedActions.map(({ id }) => id)).toEqual([9, 8]);
    expect(self.embeddedInfos.visibleEmbeddedActions).toEqual([8, 9]);
});

test("deletion does not navigate away from an action selected while layout saving waited", async () => {
    const pendingSave = new Deferred();
    const saving = new Deferred();
    const action = {
        id: 7,
        name: "Deleted",
        parent_action_id: 1,
        parent_res_model: "foo",
        action_id: 2,
    };
    let navigations = 0;
    const self = {
        embeddedInfos: {
            embeddedActions: [action],
            visibleEmbeddedActions: [7],
            currentEmbeddedAction: action,
        },
        orm: { unlink: async () => true },
        configHandler: {
            setEmbeddedActionsConfig: () => {
                saving.resolve();
                return pendingSave;
            },
        },
        actionService: { doAction: () => navigations++ },
        _actionContext: () => ({}),
    };
    const deletion = EmbeddedActions.prototype.removeAction.call(self, action);
    await saving;
    self.embeddedInfos.currentEmbeddedAction = { ...action, id: 8 };
    pendingSave.resolve(true);
    await deletion;
    makeLogger("web.search.correctness").logic("deletion-after-navigation", () => ({
        navigations,
    }));
    expect(navigations).toBe(0);
});

describe("EmbeddedActions.toggleActionVisibility", () => {
    test("toggles and persists a copy on success", async () => {
        /** @type {any} */
        let savedConfig = null;
        const self = {
            embeddedInfos: { visibleEmbeddedActions: [7] },
            configHandler: {
                setEmbeddedActionsConfig: async (/** @type {any} */ config) => {
                    savedConfig = config;
                    return true;
                },
            },
        };

        await EmbeddedActions.prototype.toggleActionVisibility.call(self, 8);

        expect(self.embeddedInfos.visibleEmbeddedActions).toEqual([7, 8]);
        expect(savedConfig.embedded_actions_visibility).toEqual([7, 8]);
        expect(savedConfig.embedded_actions_visibility).not.toBe(
            self.embeddedInfos.visibleEmbeddedActions,
        );
    });

    for (const outcomes of [
        [false, true],
        [false, false],
        [true, false],
    ]) {
        test(`overlapping visibility writes agree with persisted settings (${outcomes})`, async () => {
            const gates = [new Deferred(), new Deferred()];
            let calls = 0;
            const handler = makeConfigHandler({
                initialConfig: { "1+": { embedded_actions_visibility: [7] } },
                orm: {
                    call: async () => {
                        if (!(await gates[calls++])) {
                            throw new Error("save refused");
                        }
                    },
                },
            });
            const self = {
                embeddedInfos: { visibleEmbeddedActions: [7] },
                configHandler: handler,
            };
            const first = EmbeddedActions.prototype.toggleActionVisibility.call(
                self,
                7,
            );
            const second = EmbeddedActions.prototype.toggleActionVisibility.call(
                self,
                8,
            );
            expect(self.embeddedInfos.visibleEmbeddedActions).toEqual([8]);
            gates[0].resolve(outcomes[0]);
            await first;
            expect(self.embeddedInfos.visibleEmbeddedActions).toEqual([8]);
            gates[1].resolve(outcomes[1]);
            await second;
            expect(self.embeddedInfos.visibleEmbeddedActions).toEqual(
                outcomes[1] ? [8] : outcomes[0] ? [] : [7],
            );
            expect(self.embeddedInfos.visibleEmbeddedActions).toEqual(
                handler.getEmbeddedActionsConfig("embedded_actions_visibility"),
            );
        });
    }

    test("persistence failure restores the visible actions (hide case)", async () => {
        const self = {
            embeddedInfos: { visibleEmbeddedActions: [7, 8] },
            configHandler: { setEmbeddedActionsConfig: async () => false },
        };

        await EmbeddedActions.prototype.toggleActionVisibility.call(self, 8);

        expect(self.embeddedInfos.visibleEmbeddedActions).toEqual([7, 8]);
    });

    test("persistence failure restores the visible actions (show case)", async () => {
        const self = {
            embeddedInfos: { visibleEmbeddedActions: [7] },
            configHandler: { setEmbeddedActionsConfig: async () => false },
        };

        await EmbeddedActions.prototype.toggleActionVisibility.call(self, 9);

        expect(self.embeddedInfos.visibleEmbeddedActions).toEqual([7]);
    });
});

describe("EmbeddedActions.toggleBar", () => {
    test("re-entrant call is ignored while a toggle is in flight", async () => {
        let applyCalls = 0;
        /** @type {(value?: unknown) => void} */
        let release;
        const gate = new Promise((resolve) => {
            release = resolve;
        });
        const self = {
            embeddedInfos: { showEmbedded: false },
            async _applyBarVisibility() {
                applyCalls++;
                await gate;
            },
        };

        const first = EmbeddedActions.prototype.toggleBar.call(self);
        const second = EmbeddedActions.prototype.toggleBar.call(self);
        release();
        await Promise.all([first, second]);

        expect(applyCalls).toBe(1);
        expect(self.embeddedInfos.showEmbedded).toBe(true);
    });

    test("a failing _applyBarVisibility releases the guard and keeps the state", async () => {
        /** @type {any} */
        const self = {
            embeddedInfos: { showEmbedded: false },
            async _applyBarVisibility() {
                throw new Error("boom");
            },
        };

        await expect(EmbeddedActions.prototype.toggleBar.call(self)).rejects.toThrow();

        expect(self.embeddedInfos.showEmbedded).toBe(false);
        expect(self._togglingBar).toBe(false);

        self._applyBarVisibility = async () => {};
        await EmbeddedActions.prototype.toggleBar.call(self);
        expect(self.embeddedInfos.showEmbedded).toBe(true);
    });
});

describe("EmbeddedActions.saveNewAction", () => {
    /**
     * @param {Object} params
     * @param {Object} params.orm
     * @param {Object} params.currentEmbeddedAction
     */
    function makeSaveSelf({ orm, currentEmbeddedAction }) {
        /** @type {any[]} */
        const notifications = [];
        return {
            embeddedInfos: {
                newActionName: "My action",
                newActionIsShared: true,
                embeddedActions: [{ id: 7, name: "Existing" }],
                currentEmbeddedAction,
                visibleEmbeddedActions: [7],
            },
            orm,
            notificationService: {
                add: (/** @type {any} */ _msg, /** @type {any} */ opts) =>
                    notifications.push(opts.type),
            },
            configHandler: { setEmbeddedActionsConfig: async () => true },
            _validateNewActionName: EmbeddedActions.prototype._validateNewActionName,
            _newActionValues: EmbeddedActions.prototype._newActionValues,
            env: {
                config: { viewType: "list", actionId: 999 },
                searchModel: {
                    globalContext: { active_id: 5 },
                    createNewFavorite: async () => 1,
                },
            },
            _notifications: notifications,
        };
    }

    test("duplicate name returns false without creating anything", async () => {
        let created = false;
        const self = makeSaveSelf({
            orm: {
                create: async () => {
                    created = true;
                    return [123];
                },
            },
            currentEmbeddedAction: {
                parent_action_id: [1, "Parent"],
                action_id: [42, "Action"],
                parent_res_model: "res.partner",
            },
        });
        self.embeddedInfos.newActionName = "Existing";

        const saved = await EmbeddedActions.prototype.saveNewAction.call(self);

        expect(saved).toBe(false);
        expect(created).toBe(false);
        expect(self._notifications).toEqual(["danger"]);
    });

    test("[id, name] tuple action_id is normalized to the id", async () => {
        /** @type {{ action_id: number, parent_action_id: number }} */
        let createdValues;
        const self = makeSaveSelf({
            orm: {
                create: async (_model, [values]) => {
                    createdValues = values;
                    return [123];
                },
            },
            currentEmbeddedAction: {
                parent_action_id: [1, "Parent"],
                action_id: [42, "Action"],
                parent_res_model: "res.partner",
            },
        });

        const saved = await EmbeddedActions.prototype.saveNewAction.call(self);

        expect(saved).toBe(true);
        expect(createdValues.action_id).toBe(42);
        expect(createdValues.parent_action_id).toBe(1);
        expect(self.embeddedInfos.visibleEmbeddedActions).toEqual([7, 123]);
        expect(self.embeddedInfos.newActionName).toBe("Custom My action");
        expect(self.embeddedInfos.newActionIsShared).toBe(false);
    });

    test("bare numeric action_id is used as-is, not replaced by the current action", async () => {
        /** @type {{ action_id: number, parent_action_id: number }} */
        let createdValues;
        const self = makeSaveSelf({
            orm: {
                create: async (_model, [values]) => {
                    createdValues = values;
                    return [123];
                },
            },
            currentEmbeddedAction: {
                parent_action_id: 1,
                action_id: 42,
                parent_res_model: "res.partner",
            },
        });

        await EmbeddedActions.prototype.saveNewAction.call(self);

        expect(createdValues.action_id).toBe(42);
    });
});

describe("EmbeddedActions.reorderFromDrop", () => {
    /**
     * @param {(number | false)[]} ids
     * @param {Function} setEmbeddedActionsConfig
     */
    function makeReorderSelf(ids, setEmbeddedActionsConfig) {
        return {
            embeddedInfos: { embeddedActions: ids.map((id) => ({ id })) },
            sortActions: EmbeddedActions.prototype.sortActions,
            configHandler: { setEmbeddedActionsConfig },
        };
    }

    /** @param {number|string} index */
    function tab(index) {
        const element = document.createElement("button");
        element.dataset.embeddedIndex = String(index);
        return element;
    }

    test("dropping after a sibling persists the new order", async () => {
        /** @type {number[] | undefined} */
        let persisted;
        const self = makeReorderSelf([7, 8, 9], async ({ embedded_actions_order }) => {
            persisted = embedded_actions_order;
            return true;
        });

        await EmbeddedActions.prototype.reorderFromDrop.call(self, {
            element: tab(2),
            previous: tab(0),
        });

        expect(persisted).toEqual([7, 9, 8]);
        expect(self.embeddedInfos.embeddedActions.map((a) => a.id)).toEqual([7, 9, 8]);
    });

    test("dropping without a previous sibling moves the tab to the front", async () => {
        /** @type {number[] | undefined} */
        let persisted;
        const self = makeReorderSelf([7, 8, 9], async ({ embedded_actions_order }) => {
            persisted = embedded_actions_order;
            return true;
        });

        await EmbeddedActions.prototype.reorderFromDrop.call(self, { element: tab(2) });

        expect(persisted).toEqual([9, 7, 8]);
        expect(self.embeddedInfos.embeddedActions.map((a) => a.id)).toEqual([9, 7, 8]);
    });

    test("an unparseable position is ignored instead of dropping the last tab", async () => {
        let calls = 0;
        const self = makeReorderSelf([7, 8, 9], async () => {
            calls++;
            return true;
        });

        await EmbeddedActions.prototype.reorderFromDrop.call(self, {
            element: tab("nope"),
            previous: tab(0),
        });

        expect(calls).toBe(0);
        expect(self.embeddedInfos.embeddedActions.map((a) => a.id)).toEqual([7, 8, 9]);
    });

    test("the main action, whose id is false, can be reordered", async () => {
        /** @type {any[] | undefined} */
        let persisted;
        const self = makeReorderSelf(
            [false, 102, 103],
            async ({ embedded_actions_order }) => {
                persisted = embedded_actions_order;
                return true;
            },
        );

        await EmbeddedActions.prototype.reorderFromDrop.call(self, {
            element: tab(0),
            previous: tab(1),
        });

        expect(persisted).toEqual([102, false, 103]);
        expect(self.embeddedInfos.embeddedActions.map((a) => a.id)).toEqual([
            102,
            false,
            103,
        ]);
    });

    for (const outcomes of [
        [false, true],
        [false, false],
        [true, false],
    ]) {
        test(`overlapping reorders recover the last saved order (${outcomes})`, async () => {
            const gates = [new Deferred(), new Deferred()];
            let calls = 0;
            const self = makeReorderSelf([7, 8, 9], () => gates[calls++]);
            const first = EmbeddedActions.prototype.reorderFromDrop.call(self, {
                element: tab(2),
            });
            const second = EmbeddedActions.prototype.reorderFromDrop.call(self, {
                element: tab(2),
            });
            expect(self.embeddedInfos.embeddedActions.map((a) => a.id)).toEqual([
                8, 9, 7,
            ]);
            gates[0].resolve(outcomes[0]);
            await first;
            expect(self.embeddedInfos.embeddedActions.map((a) => a.id)).toEqual([
                8, 9, 7,
            ]);
            gates[1].resolve(outcomes[1]);
            await second;
            const expected = outcomes[1]
                ? [8, 9, 7]
                : outcomes[0]
                  ? [9, 7, 8]
                  : [7, 8, 9];
            makeLogger("web.search.improve").logic("reorder-settled", () => ({
                outcomes,
                actual: self.embeddedInfos.embeddedActions,
            }));
            expect(self.embeddedInfos.embeddedActions.map((a) => a.id)).toEqual(
                expected,
            );
        });
    }

    test("a failed reorder does not resurrect an action deleted between drops", async () => {
        const gates = [new Deferred(), new Deferred()];
        let calls = 0;
        const self = makeReorderSelf([7, 8, 9], () => gates[calls++]);
        const first = EmbeddedActions.prototype.reorderFromDrop.call(self, {
            element: tab(2),
        });
        self.embeddedInfos.embeddedActions = self.embeddedInfos.embeddedActions.filter(
            ({ id }) => id !== 7,
        );
        const second = EmbeddedActions.prototype.reorderFromDrop.call(self, {
            element: tab(1),
        });
        gates[0].resolve(false);
        await first;
        gates[1].resolve(false);
        await second;
        expect(self.embeddedInfos.embeddedActions.map(({ id }) => id)).toEqual([8, 9]);
    });

    test("a position outside the bar is ignored", async () => {
        let calls = 0;
        const self = makeReorderSelf([7, 8, 9], async () => {
            calls++;
            return true;
        });

        await EmbeddedActions.prototype.reorderFromDrop.call(self, {
            element: tab(404),
            previous: tab(0),
        });

        expect(calls).toBe(0);
        expect(self.embeddedInfos.embeddedActions.map((a) => a.id)).toEqual([7, 8, 9]);
    });
});

describe("EmbeddedActionsBar rendering", () => {
    class EmbeddedActionsFoo extends models.Model {
        _name = "embedded.actions.foo";
        name = fields.Char();
        _records = [{ id: 1, name: "r1" }];
    }
    defineModels([EmbeddedActionsFoo]);

    const embeddedAction = (id, name) => ({
        id,
        name,
        parent_action_id: [7, "Parent"],
        parent_res_model: "embedded.actions.foo",
        action_id: [10 + id, `A${id}`],
        user_id: 2,
        is_deletable: true,
        context: {},
    });

    test.tags("desktop");
    test("toggling a tab's visibility re-renders the desktop bar", async () => {
        onRpc("res.users.settings", "set_embedded_actions_setting", () => true);
        onRpc("res.users.settings", "get_embedded_actions_settings", () => ({}));

        const controlPanel = await mountWithSearch(
            ControlPanel,
            { resModel: "embedded.actions.foo" },
            {
                embeddedActions: [
                    embeddedAction(1, "Tab One"),
                    embeddedAction(2, "Tab Two"),
                ],
                parentActionId: 7,
                currentEmbeddedActionId: 1,
                actionId: 7,
            },
        );

        const embeddedActions = controlPanel.embeddedActions;
        embeddedActions.embeddedInfos.showEmbedded = true;
        embeddedActions.embeddedInfos.visibleEmbeddedActions = [1, 2];
        await animationFrame();
        expect(".o_embedded_actions button.o_draggable").toHaveCount(2);

        await embeddedActions.toggleActionVisibility(2);
        await animationFrame();
        expect(".o_embedded_actions button.o_draggable").toHaveCount(1);

        await embeddedActions.toggleActionVisibility(2);
        await animationFrame();
        expect(".o_embedded_actions button.o_draggable").toHaveCount(2);
    });
});

describe("EmbeddedActions.isVisible", () => {
    test("an action outside the saved set is hidden", () => {
        const infos = { visibleEmbeddedActions: [7] };
        expect(EmbeddedActions.isVisible(infos, /** @type {any} */ ({ id: 7 }))).toBe(
            true,
        );
        expect(EmbeddedActions.isVisible(infos, /** @type {any} */ ({ id: 8 }))).toBe(
            false,
        );
    });

    test("showAllEmbeddedActions shows one the saved set omits", () => {
        const infos = { visibleEmbeddedActions: [7], showAllEmbeddedActions: true };
        expect(EmbeddedActions.isVisible(infos, /** @type {any} */ ({ id: 7 }))).toBe(
            true,
        );
        expect(EmbeddedActions.isVisible(infos, /** @type {any} */ ({ id: 8 }))).toBe(
            true,
        );
    });

    test("the flag is read per call, so it survives a set that arrives later", () => {
        /** @type {Parameters<typeof EmbeddedActions.isVisible>[0]} */
        const infos = {
            visibleEmbeddedActions: [],
            showAllEmbeddedActions: true,
        };
        expect(EmbeddedActions.isVisible(infos, /** @type {any} */ ({ id: 8 }))).toBe(
            true,
        );
        infos.visibleEmbeddedActions = [7];
        expect(EmbeddedActions.isVisible(infos, /** @type {any} */ ({ id: 8 }))).toBe(
            true,
        );
    });
});

describe("EmbeddedActionsDropdown", () => {
    /**
     * @param {Object} [embeddedActions]
     * @param {Object} [embeddedInfos]
     */
    function makeDropdown(embeddedActions = {}, embeddedInfos = {}) {
        const dropdown = Object.create(EmbeddedActionsDropdown.prototype);
        const infos = {
            visibleEmbeddedActions: [1, 2],
            embeddedActions: [{ id: 1 }, { id: 2 }],
            currentEmbeddedAction: { id: 1 },
            newActionIsShared: false,
            newActionName: "",
            showEmbedded: true,
            ...embeddedInfos,
        };
        dropdown.props = {
            embeddedActions: { embeddedInfos: infos, ...embeddedActions },
        };
        dropdown.state = { embeddedInfos: infos };
        dropdown.newActionNameRef = { el: null };
        return dropdown;
    }

    test("setVisibility delegates to the model", async () => {
        const toggled = [];
        const dropdown = makeDropdown({
            toggleActionVisibility: async (/** @type {any} */ id) => {
                toggled.push(id);
            },
        });
        await dropdown.setVisibility(2);
        expect(toggled).toEqual([2]);
    });

    test("onEmbeddedActionClick opens the action through the model", async () => {
        const opened = [];
        const dropdown = makeDropdown({
            openAction: async (/** @type {any} */ a) => {
                opened.push(a.id);
            },
        });
        await dropdown.onEmbeddedActionClick({ id: 2 });
        expect(opened).toEqual([2]);
    });

    test("openConfirmationDialog delegates to the model", () => {
        const asked = [];
        const dropdown = makeDropdown({
            confirmDelete: (/** @type {any} */ a) => asked.push(a.id),
        });
        dropdown.openConfirmationDialog({ id: 2 });
        expect(asked).toEqual([2]);
    });

    test("onShareCheckboxChange flips the shared flag both ways", () => {
        const dropdown = makeDropdown();
        expect(dropdown.state.embeddedInfos.newActionIsShared).toBe(false);
        dropdown.onShareCheckboxChange();
        expect(dropdown.state.embeddedInfos.newActionIsShared).toBe(true);
        dropdown.onShareCheckboxChange();
        expect(dropdown.state.embeddedInfos.newActionIsShared).toBe(false);
    });

    test("saveNewAction refocuses the name input only when the save is refused", async () => {
        let stopped = 0;
        let focused = 0;
        const dropdown = makeDropdown({ saveNewAction: async () => false });
        dropdown.newActionNameRef = { el: { focus: () => focused++ } };

        await dropdown.saveNewAction({ stopPropagation: () => stopped++ });
        expect(stopped).toBe(1);
        expect(focused).toBe(1);

        dropdown.props.embeddedActions.saveNewAction = async () => true;
        await dropdown.saveNewAction({ stopPropagation: () => stopped++ });
        expect(stopped).toBe(1);
        expect(focused).toBe(1);
    });

    test("onDeleteKeydown opens the dialog only for an activation key", () => {
        const asked = [];
        const dropdown = makeDropdown({
            confirmDelete: (/** @type {any} */ a) => asked.push(a.id),
        });
        /** @param {string} key */
        const ev = (key) => ({
            key,
            preventDefault: () => {},
            stopPropagation: () => {},
        });
        dropdown.onDeleteKeydown(ev("a"), { id: 2 });
        expect(asked).toEqual([]);
        dropdown.onDeleteKeydown(ev("Enter"), { id: 2 });
        expect(asked).toEqual([2]);
    });

    test("getDropdownClass reads visibility on desktop and currency on mobile", () => {
        const dropdown = makeDropdown({}, { visibleEmbeddedActions: [1] });
        dropdown.env = { isSmall: false };
        expect(dropdown.getDropdownClass({ id: 1 })).toBe("selected");
        expect(dropdown.getDropdownClass({ id: 2 })).toBe("");

        dropdown.env = { isSmall: true };
        expect(dropdown.getDropdownClass({ id: 1 })).toBe("selected");
        expect(dropdown.getDropdownClass({ id: 2 })).toBe("");
    });
});
