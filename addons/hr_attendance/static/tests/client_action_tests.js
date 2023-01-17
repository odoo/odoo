/** @odoo-module **/

import { barcodeService } from "@barcodes/barcode_service";
import { getFixture, makeDeferred, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { companyService } from "@web/webclient/company_service";

const serviceRegistry = registry.category("services");

let serverData;
let target;

QUnit.module("Client Actions", (hooks) => {
    hooks.beforeEach(() => {
        // serverData = getActionManagerServerData();
        serverData = {
            models: {
                "hr.employee": {
                    fields: {
                        name: { string: "Name", type: "char" },
                        attendance_state: {
                            string: "State",
                            type: "selection",
                            selection: [
                                ["checked_in", "In"],
                                ["checked_out", "Out"],
                            ],
                            default: 1,
                        },
                        user_id: { string: "user ID", type: "integer" },
                        barcode: { string: "barcode", type: "integer" },
                        hours_today: { string: "Hours today", type: "float" },
                        overtime: { string: "Overtime", type: "float" },
                    },
                    records: [
                        {
                            id: 1,
                            name: "Employee A",
                            attendance_state: "checked_out",
                            user_id: 1,
                            barcode: 1,
                        },
                        {
                            id: 2,
                            name: "Employee B",
                            attendance_state: "checked_out",
                            user_id: 2,
                            barcode: 2,
                        },
                    ],
                },
                "res.company": {
                    fields: {
                        name: { string: "Name", type: "char" },
                        attendance_kiosk_mode: { type: "char" },
                        attendance_barcode_source: { type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            name: "Company A",
                            attendance_kiosk_mode: "barcode_manual",
                            attendance_barcode_source: "front",
                        },
                    ],
                },
            },

            actions: {
                "hr_attendance.hr_attendance_action_kiosk_mode": {
                    type: "ir.actions.client",
                    tag: "hr_attendance_kiosk_mode",
                },
            },
        };
        target = getFixture();

        serviceRegistry.add("barcode", barcodeService);
        serviceRegistry.add("company", companyService);
    });

    QUnit.test("My attendances: simple rendering", async function (assert) {
        patchWithCleanup(session, {
            uid: 1,
        });

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "hr_attendance_my_attendances",
        });

        assert.strictEqual(
            target.querySelector(".o_hr_attendance_kiosk_mode h1").textContent,
            "Employee A",
            "should have rendered the client action without crashing"
        );
    });

    QUnit.test("Kiosk Mode: simple rendering", async function (assert) {
        patchWithCleanup(session, {
            uid: 1,
            user_companies: {
                current_company: 1,
                allowed_companies: {
                    1: { id: 1 },
                },
            },
        });

        let rpcCount = 0;
        const mockRPC = async (route, args) => {
            if (args.method === "attendance_scan" && args.model === "hr.employee") {
                rpcCount++;
                return serverData.models["hr.employee"].records.find((r) => r.id === args.args[0]);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "hr_attendance_kiosk_mode",
        });

        const { barcode } = webClient.env.services;
        barcode.bus.trigger("barcode_scanned", { barcode: 1 });
        barcode.bus.trigger("barcode_scanned", { barcode: 1 });
        assert.strictEqual(rpcCount, 1, "RPC call should have been done only once.");

        barcode.bus.trigger("barcode_scanned", { barcode: 2 });
        assert.strictEqual(rpcCount, 1, "RPC call should have been done only once.");
    });

    QUnit.test("Attendance Greeting Message Test", async function (assert) {
        patchWithCleanup(session, {
            uid: 1,
            user_companies: {
                current_company: 1,
                allowed_companies: {
                    1: { id: 1 },
                },
            },
        });

        let rpcCount = 0;
        let def;

        const actions = [
            {
                type: "ir.actions.client",
                tag: "hr_attendance_greeting_message",
                attendance: {
                    check_in: "2018-09-20 13:41:13",
                    employee_id: [1],
                },
                next_action: "hr_attendance.hr_attendance_action_kiosk_mode",
            },
            {
                type: "ir.actions.client",
                tag: "hr_attendance_kiosk_mode",
            },
            {
                type: "ir.actions.client",
                tag: "hr_attendance_greeting_message",
                attendance: {
                    check_in: "2018-09-20 13:41:13",
                    check_out: "2018-09-20 14:41:13",
                    employee_id: [1],
                },
                next_action: "hr_attendance.hr_attendance_action_kiosk_mode",
            },
        ];

        const mockRPC = async (route, args) => {
            if (args.method === "attendance_scan" && args.model === "hr.employee") {
                await def;
                return {
                    action: actions[rpcCount++],
                };
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, {
            type: "ir.actions.client",
            tag: "hr_attendance_kiosk_mode",
        });
        assert.containsOnce(target, ".o_hr_attendance_kiosk_welcome_row");

        const { barcode } = webClient.env.services;
        barcode.bus.trigger("barcode_scanned", { barcode: 1 });
        await nextTick();
        assert.strictEqual(rpcCount, 1, "RPC call should have been done only once.");
        assert.containsNone(target, ".o_hr_attendance_kiosk_welcome_row");
        assert.strictEqual(
            target.querySelector(".o_hr_attendance_message_message").textContent,
            "Good afternoon"
        );
        assert.strictEqual(
            target
                .querySelector(".o_hr_attendance_kiosk_mode div[role='status']")
                .textContent.trim(),
            "Checked in at 09/20/2018 14:41:13"
        );

        def = makeDeferred();
        barcode.bus.trigger("barcode_scanned", { barcode: 1 });
        barcode.bus.trigger("barcode_scanned", { barcode: 1 });
        def.resolve();
        await nextTick();
        assert.strictEqual(rpcCount, 2, "RPC call should have been done only once.");
        assert.containsOnce(target, ".o_hr_attendance_kiosk_mode");

        barcode.bus.trigger("barcode_scanned", { barcode: 1 });
        await nextTick();
        assert.strictEqual(rpcCount, 3, "RPC call should have been done only once.");
        assert.containsNone(target, ".o_hr_attendance_kiosk_welcome_row");
        assert.strictEqual(
            target.querySelector(".o_hr_attendance_message_message").textContent,
            "Have a good afternoon"
        );
        assert.strictEqual(
            target
                .querySelector(".o_hr_attendance_kiosk_mode div[role='status']")
                .textContent.trim(),
            "Checked out at 09/20/2018 15:41:13"
        );
    });
});
