// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Input } from "@web/components/tree_editor/tree_editor_components";

describe.current.tags("headless");

class Host extends Component {
    static template = xml`<Input value="this.displayed" update.bind="this.update" startEmpty="this.props.startEmpty"/>`;
    static components = { Input };
    static props = ["*"];
    /** @type {{ value: number }} */
    state;
    setup() {
        /** @type {{ value: number }} */
        this.state = useState({ value: 7 });
    }
    get displayed() {
        return String(/** @type {any} */ (this.state).value);
    }
    update(/** @type {any} */ raw) {
        const parsed = Number.parseInt(raw, 10);
        /** @type {any} */ (this.state).value = Number.isNaN(parsed)
            ? /** @type {any} */ (this.state).value
            : parsed;
    }
}

test("a spelling that parses to the stored value is replaced by the canonical one", async () => {
    await mountWithCleanup(Host, { props: {} });
    expect("input").toHaveValue("7");

    await contains("input").edit("007");
    await animationFrame();
    expect("input").toHaveValue("7", {
        message: "007 parses to 7, which is already stored -- the box must show 7",
    });
});

test("an entry the parse rejects is replaced too", async () => {
    await mountWithCleanup(Host, { props: {} });

    await contains("input").edit("azerty");
    await animationFrame();
    expect("input").toHaveValue("7", {
        message: "the editor kept 7, so the input must not keep 'azerty'",
    });
});

test("a real change still lands, and startEmpty is left alone", async () => {
    await mountWithCleanup(Host, { props: {} });

    await contains("input").edit("12");
    await animationFrame();
    expect("input").toHaveValue("12");

    await mountWithCleanup(Host, { props: { startEmpty: true } });
    expect("input:last").toHaveValue("");
});
