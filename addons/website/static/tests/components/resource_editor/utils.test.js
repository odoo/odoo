import { describe, expect, test } from "@odoo/hoot";

import {
    findOperationTarget,
    getOperationRows,
    getOperationTargetRows,
    parseTargetArch,
} from "@website/components/resource_editor/utils";

function attributesArch(expr, attribute = `<attribute name="class" add="added" separator=" "/>`) {
    return `<data><xpath expr="${expr}" position="attributes">${attribute}</xpath></data>`;
}

function view(arch, { hasInheritId = false } = {}) {
    return { arch, inherit_id: hasInheritId && [1, "parent"] };
}

function getOperations(arch) {
    return parseTargetArch(view(arch, { hasInheritId: true }))?.operations ?? null;
}

function xpathOperation(expr) {
    return getOperations(attributesArch(expr))[0];
}

function findTarget(arch, expr) {
    return findOperationTarget(parseTargetArch(view(arch)).root, null, xpathOperation(expr));
}

describe("findOperationTarget", () => {
    test("finds the target", () => {
        const target = findTarget(`<t><div/><div id="target"/></t>`, "//div[@id='target']");
        expect(target.getAttribute("id")).toBe("target");
    });

    test("handles hasclass", () => {
        const target = findTarget(
            `<t><div class="foobar"/><div id="target" class="bar foo"/></t>`,
            "//div[hasclass('foo')]"
        );
        expect(target.getAttribute("id")).toBe("target");
    });

    test("handles target not found", () => {
        expect(findTarget(`<t><div/></t>`, "//div[@id='target']")).toBe(null);
    });

    test("ignores the operations in the arch of a view with an inherit_id", () => {
        const arch = `<data>
            <header position="attributes"><attribute name="class">x</attribute></header>
            <xpath expr="//main" position="inside"><header id="inserted"/></xpath>
        </data>`;
        const { root, operations } = parseTargetArch(view(arch, { hasInheritId: true }));
        const target = findOperationTarget(root, operations, xpathOperation("//header"));
        expect(target.getAttribute("id")).toBe("inserted");
    });

    test("ignores the move instructions in the arch of a view with an inherit_id", () => {
        const arch = `<data>
            <xpath expr="//main" position="before">
                <header position="move"/>
                <header id="inserted"/>
            </xpath>
        </data>`;
        const { root, operations } = parseTargetArch(view(arch, { hasInheritId: true }));
        const target = findOperationTarget(root, operations, xpathOperation("//header"));
        expect(target.getAttribute("id")).toBe("inserted");
    });

    test("does not locate absolute or positional expressions", () => {
        const arch = `<t><div/><div/></t>`;
        expect(findTarget(arch, "/t/div")).toBe(null);
        expect(findTarget(arch, "//div[2]")).toBe(null);
    });
});

describe("getOperationTargetRows", () => {
    function getTargetRows(arch, exprs) {
        return getOperationTargetRows(view(arch), exprs.map(xpathOperation));
    }

    test("returns the row where the opening tag of the target ends", () => {
        const arch = [
            "<t>",
            "    <div/>",
            '    <div id="target"',
            '         class="x">',
            "        y",
            "    </div>",
            "</t>",
        ].join("\n");
        expect(getTargetRows(arch, ["//div[@id='target']"])).toEqual([3]);
    });

    test("ignores comments, CDATA sections and '>' in attribute values", () => {
        const arch = [
            "<t>",
            "    <!-- <div> -->",
            "    <![CDATA[ <div> ]]>",
            '    <div t-if="a > b"',
            '         class="x"/>',
            "</t>",
        ].join("\n");
        expect(getTargetRows(arch, ["//div"])).toEqual([4]);
    });

    test("counts the root among the elements sharing the target's tag name", () => {
        const arch = ["<t>", '    <t t-if="x"/>', "</t>"].join("\n");
        expect(getTargetRows(arch, ["//t[@t-if]"])).toEqual([1]);
    });

    test("handles several operations, with or without target", () => {
        const arch = ["<t>", "<div>", "<span/>", "</div>", "</t>"].join("\n");
        expect(getTargetRows(arch, ["//span", "//div", "//p"])).toEqual([2, 1, null]);
    });

    test("returns null when the arch is not well-formed", () => {
        expect(getTargetRows("<t><div></t>", ["//div"])).toBe(null);
    });
});

describe("getOperationRows", () => {
    test("returns the row of each operation", () => {
        const arch = [
            "<data>",
            '    <xpath expr="//main"',
            '           position="inside">',
            "        <div/>",
            "    </xpath>",
            '    <header position="attributes"/>',
            "</data>",
        ].join("\n");
        expect(getOperationRows(view(arch, { hasInheritId: true }))).toEqual([2, 5]);
    });

    test("returns no row for a view without an inherit_id", () => {
        expect(getOperationRows(view("<t><div/></t>"))).toEqual([]);
    });

    test("returns null when the arch is not well-formed", () => {
        expect(getOperationRows(view("<data><xpath></data>", { hasInheritId: true }))).toBe(null);
    });
});
