// @ts-check

import { destroy, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    defineModels,
    fields,
    models,
    mountView,
    mountWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { useListSelection } from "@web/views/list/list_selection";

const LONG_TOUCH_THRESHOLD = 400;

test("a cancelled touch on a rendered list row does not select it", async () => {
    class Partner extends models.Model {
        name = fields.Char();
        _records = [{ id: 1, name: "Partner" }];
    }
    defineModels([Partner, ...Object.values(webModels)]);
    await mountView({
        type: "list",
        resModel: "partner",
        arch: '<list><field name="name"/></list>',
    });
    const row = queryOne(".o_data_row");
    row.dispatchEvent(new Event("touchstart", { bubbles: true }));
    row.dispatchEvent(new Event("touchcancel", { bubbles: true }));
    await advanceTime(2000);

    expect(".o_data_row").not.toHaveClass("o_data_row_selected");

    // Positive control: cancellation must not permanently disable long-touch selection.
    row.dispatchEvent(new Event("touchstart", { bubbles: true }));
    await advanceTime(2000);
    expect(".o_data_row").toHaveClass("o_data_row_selected");
    row.dispatchEvent(new Event("touchend", { bubbles: true }));
    await advanceTime(2000);
    expect(".o_data_row").toHaveClass("o_data_row_selected");
});

function mountSelectionHost(/** @type {any} */ onToggle) {
    class Host extends Component {
        static template = xml`<div/>`;
        static props = {};
        /** @type {ReturnType<typeof useListSelection>} */
        sel;

        setup() {
            this.sel = useListSelection(
                {
                    getProps: () =>
                        /** @type {any} */ ({ list: { selection: [], records: [] } }),
                    getAllowSelectors: () => true,
                    toggleRecordSelection: onToggle,
                    getEnv: () => ({ isSmall: true }),
                },
                { longTouchThreshold: LONG_TOUCH_THRESHOLD },
            );
        }
    }
    return mountWithCleanup(Host);
}

test("a pending long touch is cancelled when the component is destroyed", async () => {
    let toggled = 0;
    const host = await mountSelectionHost(() => toggled++);

    host.sel.onRowTouchStart(
        /** @type {any} */ ({ id: "rec1" }),
        /** @type {any} */ ({ stopPropagation() {} }),
    );
    destroy(host);
    await advanceTime(LONG_TOUCH_THRESHOLD * 2);

    expect(toggled).toBe(0);
});

test("a long touch that completes before destroy still toggles selection", async () => {
    let toggled = 0;
    const host = await mountSelectionHost(() => toggled++);

    host.sel.onRowTouchStart(
        /** @type {any} */ ({ id: "rec1" }),
        /** @type {any} */ ({ stopPropagation() {} }),
    );
    await advanceTime(LONG_TOUCH_THRESHOLD * 2);

    expect(toggled).toBe(1);
});
