import { describe, expect, test } from "@odoo/hoot";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { ImStatus } from "@mail/core/common/im_status";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

async function mountStatus(im_status) {
    await mountWithCleanup(ImStatus, { props: { persona: { im_status } } });
}

test("a located status renders the location icon and the presence colour", async () => {
    await mountStatus("home_busy");
    expect(".fa-house").toHaveCount(1);
    expect(".fa-house").toHaveClass("text-danger");
    expect(".fa-circle").toHaveCount(0);
});

test("every location word is rendered", async () => {
    for (const [status, selector] of [
        ["home_online", ".fa-house"],
        ["office_away", ".fa-building"],
        ["other_offline", ".fa-location-dot"],
    ]) {
        await mountStatus(status);
        expect(selector).toHaveCount(1, { message: status });
    }
});

test("a plain status falls through to mail's own icon", async () => {
    await mountStatus("online");
    expect(".fa-circle").toHaveClass("text-success");
    expect(".fa-house").toHaveCount(0);
});

test("a status another module owns falls through to mail's own icon", async () => {
    await mountStatus("leave_offline");
    // Not only "none of ours": something must still be drawn, or this control
    // would pass over a template that renders nothing at all.
    expect(".o-mail-ImStatus i").toHaveCount(1);
    expect(".fa-house").toHaveCount(0);
    expect(".fa-building").toHaveCount(0);
    expect(".fa-location-dot").toHaveCount(0);
});
