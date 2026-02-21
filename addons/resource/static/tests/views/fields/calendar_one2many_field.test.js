import { expect, test } from "@web/../lib/hoot/hoot";
import { mountView } from "@web/../tests/_framework/view_test_helpers";
import { defineResourceModels } from "../../resource_test_helpers";

defineResourceModels();

test.tags("desktop");
test(`variable resource calendar visible in the form`, async () => {
    await mountView({
        resId: 1,
        resModel: "resource.calendar",
        type: "form",
    });
    expect(".o_calendar_renderer").toBeDisplayed({
        message: "The calendar should be displayed in the form of a variable resource calendar",
    });
});
