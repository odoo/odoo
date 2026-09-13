import { openFormView, start, startServer } from "@mail/../tests/mail_test_helpers";
import { defineMrpModels } from "@mrp/../tests/mrp_test_helpers";
import { getStateDecorator } from "@mrp/components/mo_overview_line/mo_overview_colors";
import { getColorClass, getForecastAction } from "@mrp/components/mrp_overview_utils";
import { MrpTimer } from "@mrp/widgets/timer";
import { describe, expect, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

describe.current.tags("desktop");
defineMrpModels();

const formatMinutes = registry.category("formatters").get("mrp_timer");

const LIVE_ARCH = `
    <form>
        <field name="state" invisible="1"/>
        <field name="duration_live" invisible="1"/>
        <field name="duration" widget="mrp_timer" readonly="1"/>
    </form>`;

test("ensure the rendering is based on minutes and seconds", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({ duration: 150.5 });
    await start();
    await openFormView("res.fake", fakeId);
    expect(".o_field_mrp_timer").toHaveText("150:30");
});

test("mrp_timer shows the live duration from the record, without an RPC", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({
        duration: 10,
        duration_live: 42.5,
        state: "progress",
    });
    onRpc("get_duration", () => {
        expect.step("get_duration");
        return 0;
    });
    await start();
    await openFormView("res.fake", fakeId, { arch: LIVE_ARCH });
    expect(".o_field_mrp_timer").toHaveText("42:30");
    expect.verifySteps([]);
});

test("mrp_timer falls back to the bound field when the record is not in progress", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({
        duration: 10,
        duration_live: 42.5,
        state: "done",
    });
    await start();
    await openFormView("res.fake", fakeId, { arch: LIVE_ARCH });
    expect(".o_field_mrp_timer").toHaveText("10:00");
});

test("mrp_timer falls back to get_duration when the view omits duration_live", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({ duration: 10, state: "progress" });
    onRpc("get_duration", () => {
        expect.step("get_duration");
        return 42.5;
    });
    await start();
    await openFormView("res.fake", fakeId, {
        arch: `
            <form>
                <field name="state" invisible="1"/>
                <field name="duration" widget="mrp_timer" readonly="1"/>
            </form>`,
    });
    expect(".o_field_mrp_timer").toHaveText("42:30");
    expect.verifySteps(["get_duration"]);
});

test("formatMinutes renders mm:ss and carries a rounded-up second into the minutes", () => {
    expect(formatMinutes(150.5)).toBe("150:30");
    expect(formatMinutes(2.999)).toBe("03:00");
    expect(formatMinutes(0.999)).toBe("01:00");
    expect(formatMinutes(10.0083)).toBe("10:00");
    expect(formatMinutes(0)).toBe("00:00");
    expect(formatMinutes(-2.999)).toBe("-03:00");
    expect(formatMinutes(false)).toBe("");
});

test("getStateDecorator maps a model+state to a bootstrap contextual class", () => {
    expect(getStateDecorator("mrp.production", "done")).toBe("text-bg-success");
    expect(getStateDecorator("mrp.workorder", "progress")).toBe("text-bg-info");
    expect(getStateDecorator("stock.picking", "assigned")).toBe("text-bg-info");
    expect(getStateDecorator("purchase.order", "done")).toBe("text-bg-info");
    expect(getStateDecorator("no.such.model", "done")).toBe("");
});

test("shared overview helpers", () => {
    expect(getColorClass("danger")).toBe("text-danger");
    expect(getColorClass("success")).toBe("text-success");
    expect(getColorClass(false)).toBe("");
    expect(getForecastAction("product.product")).toBe("action_product_forecast_report");
    expect(getForecastAction("product.template")).toBe(
        "action_product_tmpl_forecast_report",
    );
    expect(getForecastAction("mrp.bom")).toBe(undefined);
});

test("MrpTimer ticks while ongoing and cleans up (no leaked timers)", async () => {
    class Parent extends Component {
        static components = { MrpTimer };
        static props = {};
        static template = xml`<div class="test-timer"><MrpTimer value="0" ongoing="true"/></div>`;
    }
    await mountWithCleanup(Parent);
    expect(".test-timer").toHaveText("00:00");
    await advanceTime(3000);
    expect(".test-timer").toHaveText("00:03");
});

test("MrpTimer stays frozen when not ongoing", async () => {
    class Parent extends Component {
        static components = { MrpTimer };
        static props = {};
        static template = xml`<div class="test-timer"><MrpTimer value="5" ongoing="false"/></div>`;
    }
    await mountWithCleanup(Parent);
    expect(".test-timer").toHaveText("05:00");
    await advanceTime(30000);
    expect(".test-timer").toHaveText("05:00");
});
