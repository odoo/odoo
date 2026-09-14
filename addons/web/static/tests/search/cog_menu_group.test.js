// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { validate } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import {
    COG_GROUP,
    COG_MENU_REGISTRY_VALIDATION,
    isActWindowView,
    isCogGroup,
} from "@web/search/cog_menu/cog_menu_group";
import {
    getActionMenuItems,
    prepareStaticActionMenuItems,
} from "@web/views/view_utils";

describe.current.tags("headless");

/** @param {Record<string, any>} [overrides] */
function makeCogMenu(overrides = {}) {
    const menu = Object.create(CogMenu.prototype);
    menu.env = /** @type {any} */ ({});
    menu.props = { items: {} };
    menu.registryItems = [];
    menu.actionItems = [];
    Object.assign(menu, overrides);
    return menu;
}

describe("COG_GROUP", () => {
    test("sections read top to bottom in the documented order", () => {
        const order = [
            COG_GROUP.DATA,
            COG_GROUP.RECORD,
            COG_GROUP.APP,
            COG_GROUP.PRINT,
            COG_GROUP.ACTIONS,
            COG_GROUP.INTEGRATE,
            COG_GROUP.DANGER,
        ];
        expect(order.toSorted((a, b) => a - b)).toEqual(order);
    });

    test("only a declared section number is a cog group", () => {
        expect(isCogGroup(COG_GROUP.APP)).toBe(true);
        expect(isCogGroup(1)).toBe(false);
        expect(isCogGroup(undefined)).toBe(false);
    });

    test("the registry validation rejects a bare group number", () => {
        const Component = class {};
        expect(() =>
            validate({ Component, groupNumber: 1 }, COG_MENU_REGISTRY_VALIDATION),
        ).toThrow();
        expect(() => validate({ Component }, COG_MENU_REGISTRY_VALIDATION)).toThrow();
        expect(() =>
            validate(
                { Component, groupNumber: COG_GROUP.DATA },
                COG_MENU_REGISTRY_VALIDATION,
            ),
        ).not.toThrow();
    });

    test("every entry registered in the cog menu declares a cog group", () => {
        const offenders = registry
            .category("cogMenu")
            .getEntries()
            .filter(([, item]) => !isCogGroup(item.groupNumber))
            .map(([key]) => key);
        expect(offenders).toEqual([]);
    });
});

describe("isActWindowView", () => {
    const env = /** @param {Record<string, any>} config */ (config) =>
        /** @type {any} */ ({ config });

    test("requires a window action", () => {
        expect(isActWindowView(env({ actionType: "ir.actions.client" }))).toBe(false);
        expect(isActWindowView(env({ actionType: "ir.actions.act_window" }))).toBe(
            true,
        );
    });

    test("narrows to the given view types", () => {
        const kanban = env({ actionType: "ir.actions.act_window", viewType: "kanban" });
        expect(isActWindowView(kanban, ["list", "kanban"])).toBe(true);
        expect(isActWindowView(kanban, ["form"])).toBe(false);
    });

    test("an env without a config is not a window view", () => {
        expect(isActWindowView(/** @type {any} */ ({}))).toBe(false);
    });
});

describe("cogItems sections", () => {
    test("print joins the sort between the app section and bound actions", () => {
        const menu = makeCogMenu({
            props: { items: { print: [{ id: 7 }] } },
            registryItems: [{ key: "app", groupNumber: COG_GROUP.APP }],
            actionItems: [
                { key: "delete", groupNumber: COG_GROUP.DANGER },
                { key: "bound", groupNumber: COG_GROUP.ACTIONS },
                { key: "duplicate", groupNumber: COG_GROUP.RECORD },
            ],
        });
        expect(menu.cogItems.map((/** @type {any} */ i) => i.key)).toEqual([
            "duplicate",
            "app",
            "print",
            "bound",
            "delete",
        ]);
    });

    test("a default slot alone is enough to show the gear", () => {
        const menu = makeCogMenu({ props: { items: {}, slots: { default: {} } } });
        expect(menu.hasItems).toBe(true);
    });
});

describe("static action menu items", () => {
    test("shared verbs take their section from the descriptor", () => {
        const { action } = getActionMenuItems(
            prepareStaticActionMenuItems({
                export: {},
                duplicate: {},
                insertInSpreadsheet: {},
                delete: {},
            }),
        );
        expect(
            Object.fromEntries(action.map((item) => [item.key, item.groupNumber])),
        ).toEqual({
            export: COG_GROUP.DATA,
            duplicate: COG_GROUP.RECORD,
            insertInSpreadsheet: COG_GROUP.INTEGRATE,
            delete: COG_GROUP.DANGER,
        });
    });

    test("an addon's own item lands in the app section", () => {
        const { action } = getActionMenuItems({
            publish: { description: "Publish", callback: () => {} },
        });
        expect(action[0].groupNumber).toBe(COG_GROUP.APP);
    });

    test("delete is flagged dangerous", () => {
        const { action } = getActionMenuItems(
            prepareStaticActionMenuItems({ delete: {} }),
        );
        expect(action[0].danger).toBe(true);
    });

    test("an unknown shared verb is refused", () => {
        expect(() => prepareStaticActionMenuItems({ noSuchVerb: {} })).toThrow();
    });
});
