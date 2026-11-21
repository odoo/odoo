import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { switchToEditMode } from "../../helpers";
import { startInteractionsWithSnippet } from "../helpers";

describe.current.tags("interaction_dev");
setupInteractionWhiteList("website.map_edit");

test("map without address: warning only rendered in edit mode", async () => {
    const { core } = await startInteractionsWithSnippet("s_map", {
        processHTML: (containerEl) => {
            delete containerEl.querySelector(".s_map").dataset.mapAddress;
        },
        startOptions: { waitForStart: true, editMode: true },
    });
    expect(".s_map .missing_option_warning").toHaveCount(0);

    await switchToEditMode(core);
    expect(".s_map .missing_option_warning").toHaveCount(1);

    // A company without address gives an empty attribute.
    queryOne(".s_map").dataset.mapAddress = "";
    await switchToEditMode(core);
    expect(".s_map .missing_option_warning").toHaveCount(1);

    core.stopInteractions();
    expect(".s_map .missing_option_warning").toHaveCount(0);
});
