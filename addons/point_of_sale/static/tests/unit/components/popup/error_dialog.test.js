import { test, expect, animationFrame, mockMatchMedia, queryOne } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { ErrorDialog } from "@web/core/errors/error_dialogs";

definePosModels();

test("shows Reload Data button on Error Dialog", async () => {
    const store = await setupAndMountPosApp();

    const addErrorDialog = async () => {
        store.dialog.add(ErrorDialog, {
            name: "OwlError",
            message: "Something went wrong",
            close: () => {},
        });
        await animationFrame();
    };

    await addErrorDialog();
    expect(".modal-footer .btn").toHaveCount(1);
    expect(".modal .modal-title").toHaveText("Oops!");
    await contains(".o-default-button").click();

    // For PWA applications
    mockMatchMedia({ ["display-mode"]: "standalone" });
    await addErrorDialog();
    expect(".modal-footer .btn").toHaveCount(2);
    const reloadDataBtn = queryOne(".modal-footer .btn-secondary");
    expect(reloadDataBtn).toHaveText("Reload Data");
    await contains(reloadDataBtn).click();

    expect(".modal .modal-title").toHaveText("Reload Data");
});
