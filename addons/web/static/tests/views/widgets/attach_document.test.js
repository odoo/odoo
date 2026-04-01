import { expect, test } from "@odoo/hoot";
import { click, manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { AttachDocumentWidget } from "@web/views/widgets/attach_document/attach_document";

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
    // FIXME: This ugly hack is needed because the input is not attached in the DOM
    // The input should be attached to the component and hidden in some way to make
    // the interaction easier and more natural.
    let fileInput;
    patchWithCleanup(AttachDocumentWidget.prototype, {
        setup() {
            super.setup();
            fileInput = this.fileInput;
        },
    });

    mockService("http", {
        post(route, params) {
            expect.step("post");
            expect(route).toBe("/web/binary/upload_attachment");
            expect(params.model).toBe("partner");
            expect(params.id).toBe(1);
            return '[{ "id": 5 }, { "id": 2 }]';
        },
    });

    onRpc(({ args, kwargs, method, model }) => {
        expect.step(method);
        if (method === "my_action") {
            expect(model).toBe("partner");
            expect(args).toEqual([1]);
            expect(kwargs.attachment_ids).toEqual([5, 2]);
            return true;
        }
        if (method === "web_save") {
            expect(args[1]).toEqual({ display_name: "yop" });
        }
        if (method === "web_read") {
            expect(args[0]).toEqual([1]);
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
    expect.verifySteps(["get_views", "web_read"]);

    await contains("[name='display_name'] input").edit("yop");
    await animationFrame();
    await click(".o_attach_document");
    await animationFrame();
    await manuallyDispatchProgrammaticEvent(fileInput, "change");
    await animationFrame();
    expect.verifySteps(["web_save", "post", "my_action", "web_read"]);
});

test("attach document widget calls action with attachment ids on a new record", async () => {
    // FIXME: This ugly hack is needed because the input is not attached in the DOM
    // The input should be attached to the component and hidden in some way to make
    // the interaction easier and more natural.
    let fileInput;
    patchWithCleanup(AttachDocumentWidget.prototype, {
        setup() {
            super.setup();
            fileInput = this.fileInput;
        },
    });

    mockService("http", {
        post(route, params) {
            expect.step("post");
            expect(route).toBe("/web/binary/upload_attachment");
            expect(params.model).toBe("partner");
            expect(params.id).toBe(2);
            return '[{ "id": 5 }, { "id": 2 }]';
        },
    });

    onRpc(({ args, kwargs, method, model }) => {
        expect.step(method);
        if (method === "my_action") {
            expect(model).toBe("partner");
            expect(args).toEqual([2]);
            expect(kwargs.attachment_ids).toEqual([5, 2]);
            return true;
        }
        if (method === "web_save") {
            expect(args[1]).toEqual({ display_name: "yop" });
        }
        if (method === "web_read") {
            expect(args[0]).toEqual([2]);
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
    expect.verifySteps(["get_views", "onchange"]);
    await contains("[name='display_name'] input").edit("yop");
    await click(".o_attach_document");
    await animationFrame();
    await manuallyDispatchProgrammaticEvent(fileInput, "change");
    await animationFrame();
    expect.verifySteps(["web_save", "post", "my_action", "web_read"]);
});
