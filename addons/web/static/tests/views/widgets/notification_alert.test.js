import { expect, test } from "@odoo/hoot";
import { mockPermission } from "@odoo/hoot-mock";
import { defineModels, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    _records = [{ id: 1 }];
}

defineModels([Partner]);

const viewData = {
    type: "form",
    resModel: "partner",
    resId: 1,
    arch: /* xml */ `<form><widget name="notification_alert"/></form>`,
};

test("notification alert should be displayed when notification denied", async () => {
    mockPermission("notifications", "denied");
    await mountView(viewData);
    expect(".o_widget_notification_alert .alert").toHaveCount(1, {
        message: "notification alert should be displayed when notification denied",
    });
});

test("notification alert should not be displayed when notification granted", async () => {
    mockPermission("notifications", "granted");
    await mountView(viewData);
    expect(".o_widget_notification_alert .alert").toHaveCount(0, {
        message: "notification alert should not be displayed when notification granted",
    });
});

test("notification alert should not be displayed when notification default", async () => {
    mockPermission("notifications", "default");
    await mountView(viewData);
    expect(".o_widget_notification_alert .alert").toHaveCount(0, {
        message: "notification alert should not be displayed when notification default",
    });
});
