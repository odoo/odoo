// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { onMounted, onWillRender } from "@odoo/owl";
import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { Deferred } from "@web/core/utils/concurrency";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { Layout } from "@web/search/layout";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { MultiRecordController } from "@web/views/multi_record_controller";

describe.current.tags("desktop");

class Foo extends models.Model {
    foo = fields.Char();
    int_field = fields.Integer();

    _records = [
        { id: 1, foo: "a", int_field: 1 },
        { id: 2, foo: "b", int_field: 2 },
        { id: 3, foo: "c", int_field: 3 },
    ];
}

defineModels([...Object.values(webModels), Foo]);

const ARCH = `
    <list>
        <field name="foo"/>
        <field name="int_field"/>
    </list>
`;

function instrumentChain() {
    /** @type {string[]} */
    /** @type {string[]} */
    const sequence = [];
    patchWithCleanup(/** @type {any} */ (MultiRecordController).prototype, {
        setup() {
            super.setup();
            onWillRender(() => {
                const model = /** @type {any} */ (this).model;
                sequence.push(`rows=${model?.root?.records?.length}`);
            });
        },
    });
    for (const [name, Cls] of /** @type {[string, any][]} */ ([
        ["MultiRecordController", MultiRecordController],
        ["Layout", Layout],
        ["ControlPanel", ControlPanel],
        ["SearchBar", SearchBar],
        ["SearchBarMenu", SearchBarMenu],
    ])) {
        patchWithCleanup(Cls.prototype, {
            setup() {
                super.setup();
                onWillRender(() => {
                    sequence.push(String(name));
                });
                onMounted(() => {
                    sequence.push(`MOUNTED:${name}`);
                });
            },
        });
    }
    return sequence;
}

describe("control-panel chain render budget", () => {
    test("the chain renders twice, and BOTH passes precede every mount", async () => {
        const sequence = instrumentChain();
        await mountView({ resModel: "foo", type: "list", arch: ARCH });
        await animationFrame();

        const renders = sequence.filter((s) => s === "ControlPanel").length;
        expect(renders).toBe(2);

        const firstMount = sequence.findIndex((s) => s.startsWith("MOUNTED:"));
        const lastRender = sequence.lastIndexOf("ControlPanel");
        expect(lastRender).toBeLessThan(firstMount);
    });

    test("the discarded first pass renders an EMPTY model", async () => {
        const sequence = instrumentChain();
        await mountView({ resModel: "foo", type: "list", arch: ARCH });
        await animationFrame();

        expect(sequence.filter((s) => s.startsWith("rows="))).toEqual([
            "rows=0",
            "rows=3",
        ]);
    });

    test("SearchBarMenu renders once per pass", async () => {
        const sequence = instrumentChain();
        await mountView({ resModel: "foo", type: "list", arch: ARCH });
        await animationFrame();

        // The first pass used to abort before reaching SearchBarMenu: the
        // controller's onWillStart awaited a has_group round trip for
        // base.group_allow_export and the records landed mid-render. The mock
        // session now seeds that group as session_info does, the lookup is a
        // cache hit, and the first pass completes before it is superseded —
        // the same one-render-per-pass budget SearchBar and ControlPanel have.
        expect(sequence.filter((s) => s === "SearchBarMenu").length).toBe(2);
        expect(sequence.filter((s) => s === "SearchBar").length).toBe(2);
    });
});

test("a SLOW load mounts the shell first — the payoff lazy: true exists for", async () => {
    const def = new Deferred();
    onRpc("web_search_read", async () => {
        await def;
    });
    const sequence = instrumentChain();
    const mounting = mountView({ resModel: "foo", type: "list", arch: ARCH });
    for (let i = 0; i < 10; i++) {
        await animationFrame();
    }

    const beforeData = [...sequence];
    expect(beforeData.filter((e) => e === "ControlPanel").length).toBe(1);
    expect(beforeData.filter((e) => e.startsWith("rows="))).toEqual(["rows=0"]);
    expect(beforeData.some((e) => e === "MOUNTED:ControlPanel")).toBe(true);

    expect(beforeData.filter((e) => e === "SearchBarMenu").length).toBe(1);

    def.resolve();
    await mounting;
    await animationFrame();

    const after = sequence.slice(beforeData.length);
    expect(after.filter((e) => e === "ControlPanel").length).toBe(1);
    expect(after.filter((e) => e.startsWith("rows="))).toEqual(["rows=3"]);
    expect(after.some((e) => e.startsWith("MOUNTED:"))).toBe(false);
});
