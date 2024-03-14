import { expect, test } from "@odoo/hoot";
import { click, setInputFiles } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    display_name = fields.Char({ string: "Displayed name" });
    _records = [
        {
            id: 1,
            display_name: "first record",
        },
    ];
}

defineModels([Partner]);

test("attach document widget calls action with attachment ids", async () => {
    mockService("http", () => ({
        post: (route, params) => {
            expect.step("post");
            expect(route).toBe("/web/binary/upload_attachment");
            expect(params.model).toBe("partner");
            expect(params.id).toBe(1);
            return '[{ "id": 5 }, { "id": 2 }]';
        },
    }));

    onRpc(async (route, params) => {
        expect.step(params.method);
        if (params.method === "my_action") {
            expect(params.model).toBe("partner");
            expect(params.args).toEqual([1]);
            expect(params.kwargs.attachment_ids).toEqual([5, 2]);
            return true;
        }
        if (params.method === "web_save") {
            expect(params.args[1]).toEqual({ display_name: "yop" });
        }
        if (params.method === "web_read") {
            expect(params.args[0]).toEqual([1]);
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
        <form>
            <widget name="attach_document" action="my_action" string="Attach document"/>
            <field name="display_name" required="1"/>
        </form>`,
    });
    expect(["get_views", "web_read"]).toVerifySteps();

    await contains("[name='display_name'] input").edit("yop");
    await animationFrame();
    click(".o_attach_document");
    await animationFrame();
    setInputFiles([]);
    await animationFrame();
    expect(["web_save", "post", "my_action", "web_read"]).toVerifySteps();
});

test("attach document widget calls action with attachment ids on a new record", async () => {
    mockService("http", () => ({
        post: (route, params) => {
            expect.step("post");
            expect(route).toBe("/web/binary/upload_attachment");
            expect(params.model).toBe("partner");
            expect(params.id).toBe(2);
            return '[{ "id": 5 }, { "id": 2 }]';
        },
    }));

    onRpc(async (route, params) => {
        expect.step(params.method);
        if (params.method === "my_action") {
            expect(params.model).toBe("partner");
            expect(params.args).toEqual([2]);
            expect(params.kwargs.attachment_ids).toEqual([5, 2]);
            return true;
        }
        if (params.method === "web_save") {
            expect(params.args[1]).toEqual({ display_name: "yop" });
        }
        if (params.method === "web_read") {
            expect(params.args[0]).toEqual([2]);
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
        <form>
            <widget name="attach_document" action="my_action" string="Attach document"/>
            <field name="display_name" required="1"/>
        </form>`,
    });
    expect(["get_views", "onchange"]).toVerifySteps();
    await contains("[name='display_name'] input").edit("yop");
    click(".o_attach_document");
    await animationFrame();
    setInputFiles([]);
    await animationFrame();
    expect(["web_save", "post", "my_action", "web_read"]).toVerifySteps();
});
