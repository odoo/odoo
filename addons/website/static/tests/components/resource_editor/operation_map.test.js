import { describe, expect, test } from "@odoo/hoot";

import { locateOperations } from "@website/components/resource_editor/operation_map";

function view(id, arch, { parentId = false, mode = parentId ? "extension" : "primary" } = {}) {
    return { id, arch, inherit_id: parentId && [parentId, `view ${parentId}`], mode };
}

function locate(views) {
    const viewsById = Object.fromEntries(views.map((v) => [v.id, v]));
    return locateOperations(viewsById).map(({ view, targetId }) => [view.id, targetId]);
}

const ADD_CLASS_ON_HEADER = `<data><xpath expr="//header" position="attributes"><attribute name="class" add="x"/></xpath></data>`;

describe("locateOperations", () => {
    test("locates an operation in the ancestor holding its target", () => {
        const located = locate([
            view(1, `<t t-name="root"><header/><main/></t>`),
            view(2, `<data><xpath expr="//main" position="inside"><div/></xpath></data>`, {
                parentId: 1,
            }),
            view(3, ADD_CLASS_ON_HEADER, { parentId: 2 }),
        ]);
        expect(located).toEqual([
            [2, 1],
            [3, 1],
        ]);
    });

    test("does not locate a target found in several ancestors", () => {
        const located = locate([
            view(1, `<t t-name="root"><header/></t>`),
            view(2, `<data><xpath expr="//header" position="after"><header/></xpath></data>`, {
                parentId: 1,
            }),
            view(3, ADD_CLASS_ON_HEADER, { parentId: 2 }),
        ]);
        expect(located).toEqual([[2, 1]]);
    });

    test("stops at the first primary ancestor", () => {
        const located = locate([
            view(1, `<t t-name="root"><header/></t>`),
            view(2, `<data><xpath expr="//header" position="after"><main/></xpath></data>`, {
                parentId: 1,
                mode: "primary",
            }),
            view(3, ADD_CLASS_ON_HEADER, { parentId: 2 }),
        ]);
        expect(located).toEqual([]);
    });
});
