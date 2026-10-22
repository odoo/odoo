import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { WebClient } from "@web/webclient/webclient";
import { WebsiteDialog } from "@website/components/dialog/dialog";

defineMailModels();

describe.current.tags("desktop");

test("a failed click leaves the dialog and its buttons usable", async () => {
    expect.errors(1);
    await mountWithCleanup(WebClient);
    getService("dialog").add(WebsiteDialog, {
        body: "Body",
        primaryTitle: "Save",
        primaryClick: () => Promise.reject(new Error("Save refused")),
    });
    await animationFrame();

    await contains(".modal-footer button:contains(Save)").click();
    await animationFrame();
    expect.verifyErrors(["Save refused"]);
    // the error shows over the dialog, which stays open with its buttons usable
    expect(".modal-footer button:contains(Save)").not.toHaveAttribute("disabled");
    expect(".modal-footer button:contains(Discard)").not.toHaveAttribute("disabled");
});
