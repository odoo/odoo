import { describe, expect, test } from "@odoo/hoot";
import { openFormView, start, startServer } from "@mail/../tests/mail_test_helpers";
import { defineMrpModels } from "@mrp/../tests/mrp_test_helpers";

describe.current.tags("desktop");
defineMrpModels();

test("ensure the rendering is based on minutes and seconds", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["res.fake"].create({ duration: 150.5 });
    await start();
    await openFormView("res.fake", fakeId);
    expect(document.querySelector(".o_field_mrp_timer").textContent).toBe("150:30");
});
