import { describe, expect, test } from "@odoo/hoot";

import { locateOperations } from "@website/components/resource_editor/operation_map";

function view(id, arch, { parentId = false, mode } = {}) {
    return {
        id,
        arch,
        inherit_id: parentId && [parentId, `view ${parentId}`],
        mode: mode || (parentId ? "extension" : "primary"),
    };
}

function getIncomingViewIds(locatedOperations, viewId) {
    return locatedOperations
        .filter(({ targetId }) => targetId === viewId)
        .map(({ view }) => view.id);
}

function indexViews(views) {
    return Object.fromEntries(views.map((v) => [v.id, v]));
}

const ADD_CLASS_ON_HEADER = `<data><xpath expr="//header" position="attributes"><attribute name="class" add="x"/></xpath></data>`;

describe("locateOperations", () => {
    test("locates an operation in the ancestor holding its target", () => {
        const views = indexViews([
            view(1, `<t t-name="root"><header/><main/></t>`),
            view(2, `<data><xpath expr="//main" position="inside"><div/></xpath></data>`, {
                parentId: 1,
            }),
            view(3, ADD_CLASS_ON_HEADER, { parentId: 2 }),
        ]);
        const locatedOperations = locateOperations(views);
        expect(getIncomingViewIds(locatedOperations, 1)).toEqual([2, 3]);
        expect(getIncomingViewIds(locatedOperations, 2)).toEqual([]);
    });

    test("does not locate ambiguous or missing targets", () => {
        const views = indexViews([
            view(1, `<t t-name="root"><header/></t>`),
            view(2, `<data><xpath expr="/t" position="inside"><header/></xpath></data>`, {
                parentId: 1,
            }),
            view(3, ADD_CLASS_ON_HEADER, { parentId: 2 }),
            view(4, `<data><xpath expr="//footer" position="after"><div/></xpath></data>`, {
                parentId: 1,
            }),
        ]);
        const locatedOperations = locateOperations(views);
        expect(getIncomingViewIds(locatedOperations, 1)).toEqual([]);
        expect(getIncomingViewIds(locatedOperations, 2)).toEqual([]);
    });

    test("stops at the first primary ancestor", () => {
        const views = indexViews([
            view(1, `<t t-name="root"><header/></t>`),
            view(2, `<data><xpath expr="//header" position="after"><main/></xpath></data>`, {
                parentId: 1,
                mode: "primary",
            }),
            view(3, ADD_CLASS_ON_HEADER, { parentId: 2 }),
        ]);
        const locatedOperations = locateOperations(views);
        expect(getIncomingViewIds(locatedOperations, 1)).toEqual([]);
        expect(getIncomingViewIds(locatedOperations, 2)).toEqual([]);
    });
});
