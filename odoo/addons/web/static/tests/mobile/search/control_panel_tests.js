/** @odoo-module **/

import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { makeWithSearch, setupControlPanelServiceRegistry } from "@web/../tests/search/helpers";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";

let serverData;
let target;

QUnit.module("Search", (hooks) => {
    hooks.beforeEach(async () => {
        setupControlPanelServiceRegistry();
        target = getFixture();
        registry.category("services").add("ui", uiService);

        serverData = {
            models: {
                foo: {
                    fields: {
                        birthday: { string: "Birthday", type: "date", store: true, sortable: true },
                        date_field: { string: "Date", type: "date", store: true, sortable: true },
                    },
                    records: [{ date_field: "2022-02-14" }],
                },
            },
            views: {
                "foo,false,search": `
                    <search>
                        <filter name="birthday" date="birthday"/>
                        <filter name="date_field" date="date_field"/>
                    </search>
                `,
            },
        };
    });

    QUnit.module("Control Panel (mobile)");

    QUnit.test("Control panel is shown/hide on top when scrolling", async (assert) => {
        await makeWithSearch({
            serverData,
            resModel: "foo",
            Component: ControlPanel,
            searchMenuTypes: ["filter"],
        });
        const contentHeight = 200;
        const sampleContent = document.createElement("div");
        sampleContent.style.minHeight = `${2 * contentHeight}px`;
        target.appendChild(sampleContent);
        const { maxHeight, overflow } = target.style;
        target.style.maxHeight = `${contentHeight}px`;
        target.style.overflow = "auto";
        target.scrollTo({ top: 50 });
        await nextTick();

        assert.hasClass(
            target.querySelector(".o_control_panel"),
            "o_mobile_sticky",
            "control panel becomes sticky when the target is not on top"
        );
        target.scrollTo({ top: -50 });
        await nextTick();

        assert.doesNotHaveClass(
            target.querySelector(".o_control_panel"),
            "o_mobile_sticky",
            "control panel is not sticky anymore"
        );
        target.style.maxHeight = maxHeight;
        target.style.overflow = overflow;
    });
});
