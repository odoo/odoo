/** @odoo-module **/

import { registry } from "@web/core/registry";
import { makeFakeLocalizationService } from "../../helpers/mock_services";
import { getFixture, click, clickEdit, clickSave } from "../../helpers/utils";
import { makeView, setupViewRegistries } from "../helpers";

let serverData;
let fixture;

QUnit.module("Widgets", ({ beforeEach }) => {
    beforeEach(() => {
        fixture = getFixture();
        setupViewRegistries();

        serverData = {
            models: {
                partner: {
                    fields: {
                        id: { type: "integer", string: "ID" },
                        sun: { type: "boolean", string: "Sun" },
                        mon: { type: "boolean", string: "Mon" },
                        tue: { type: "boolean", string: "Tue" },
                        wed: { type: "boolean", string: "Wed" },
                        thu: { type: "boolean", string: "Thu" },
                        fri: { type: "boolean", string: "Fri" },
                        sat: { type: "boolean", string: "Sat" },
                    },
                    records: [
                        {
                            id: 1,
                            sun: false,
                            mon: false,
                            tue: false,
                            wed: false,
                            thu: false,
                            fri: false,
                            sat: false,
                        },
                    ],
                },
            },
        };
    });

    QUnit.module("WeekDays");

    QUnit.test("simple week recurrence widget", async (assert) => {
        assert.expect(14);

        let writeCall = 0;
        registry.category("services", makeFakeLocalizationService({ weekStart: 1 }));

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <widget name="week_days" />
                        </group>
                    </sheet>
                </form>
            `,
            mockRPC(route, { args, method }) {
                if (method === "write") {
                    writeCall++;
                    if (writeCall === 1) {
                        assert.ok(args[1].sun, "value of sunday should be true");
                    }
                    if (writeCall === 2) {
                        assert.notOk(args[1].sun, "value of sunday should be false");
                        assert.ok(args[1].mon, "value of monday should be true");
                        assert.ok(args[1].tue, "value of tuesday should be true");
                    }
                }
            },
        });

        assert.containsN(
            fixture,
            "input:disabled",
            7,
            "all inputs should be disabled in readonly mode"
        );
        const labelsTexts = [...fixture.querySelectorAll(".o_recurrent_weekday_label")].map((el) =>
            el.innerText.trim()
        );
        assert.deepEqual(
            labelsTexts,
            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "labels should be short week names"
        );

        await clickEdit(fixture);
        assert.containsNone(
            fixture,
            ".custom-control input:disabled",
            "all inputs should be enabled in readonly mode"
        );

        await click(fixture.querySelector("td:nth-child(7) input"));
        assert.ok(
            fixture.querySelector("td:nth-child(7) input").checked,
            "sunday checkbox should be checked"
        );
        await clickSave(fixture);

        await clickEdit(fixture);
        await click(fixture.querySelector("td:nth-child(1) input"));
        assert.ok(
            fixture.querySelector("td:nth-child(1) input").checked,
            "monday checkbox should be checked"
        );

        await click(fixture.querySelector("td:nth-child(2) input"));
        assert.ok(
            fixture.querySelector("td:nth-child(2) input").checked,
            "tuesday checkbox should be checked"
        );

        // uncheck Sunday checkbox and check write call
        await click(fixture.querySelector("td:nth-child(7) input"));
        assert.notOk(
            fixture.querySelector("td:nth-child(7) input").checked,
            "sunday checkbox should be unchecked"
        );

        await clickSave(fixture);
        assert.notOk(
            fixture.querySelector("td:nth-child(7) input").checked,
            "sunday checkbox should be unchecked"
        );
        assert.ok(
            fixture.querySelector("td:nth-child(1) input").checked,
            "monday checkbox should be checked"
        );
        assert.ok(
            fixture.querySelector("td:nth-child(2) input").checked,
            "tuesday checkbox should be checked"
        );
    });

    QUnit.test(
        "week recurrence widget show week start as per language configuration",
        async (assert) => {
            registry.category("services", makeFakeLocalizationService({ weekStart: 5 }));

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <widget name="week_days" />
                            </group>
                        </sheet>
                    </form>
                `,
            });

            const labels = [...fixture.querySelectorAll(".o_recurrent_weekday_label")].map((el) =>
                el.textContent.trim()
            );
            assert.deepEqual(
                labels,
                ["Fri", "Sat", "Sun", "Mon", "Tue", "Wed", "Thu"],
                "labels should be short week names"
            );
        }
    );
});
