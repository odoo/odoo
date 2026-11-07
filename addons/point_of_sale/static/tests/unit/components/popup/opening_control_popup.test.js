import { test, expect } from "@odoo/hoot";
import {
    makeServerError,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { OpeningControlPopup } from "@point_of_sale/app/components/popups/opening_control_popup/opening_control_popup";

definePosModels();

const setupOpeningControlPopup = async ({ sessionDeleted }) => {
    const store = await setupPosEnv();
    store.session.state = "opening_control";
    patchWithCleanup(browser.location, {
        reload() {
            expect.step("reload");
        },
    });
    onRpc("pos.session", "set_opening_control", () => {
        throw makeServerError({ type: "MissingError" });
    });
    onRpc("pos.session", "search_count", () => (sessionDeleted ? 0 : 1));
    const popup = await mountWithCleanup(OpeningControlPopup, {
        props: { close: () => expect.step("close") },
    });
    return { store, popup };
};

test("confirm reloads the page when the session has been deleted", async () => {
    const { store, popup } = await setupOpeningControlPopup({ sessionDeleted: true });

    await popup.confirm();

    expect.verifySteps(["reload"]);
    expect(store.session.state).toBe("opening_control");
});

test("confirm rethrows the error when the session still exists", async () => {
    const { store, popup } = await setupOpeningControlPopup({ sessionDeleted: false });

    await expect(popup.confirm()).rejects.toThrow();

    expect.verifySteps([]);
    expect(store.session.state).toBe("opening_control");
});
