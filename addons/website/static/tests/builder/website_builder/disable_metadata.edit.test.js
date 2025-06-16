import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { switchToEditMode } from "../../helpers";

setupInteractionWhiteList("website.disable_metadata");

test("div with metadata are not editable", async () => {
    const { core } = await startInteractions(
        `
        <div class="root">
            <div>editable</div>
            <div class="o_we_bg_filter"></div>
            <div class="o_we_shape"></div>
        </div>
        `,
        { editMode: true }
    );
    expect(queryOne(".root")).toHaveInnerHTML(
        `<div> editable </div> <div class="o_we_bg_filter"> </div> <div class="o_we_shape"> </div>`
    );
    await switchToEditMode(core);
    // we check now that the 2 divs with metadata are non editable
    expect(queryOne(".root")).toHaveInnerHTML(
        `<div> editable </div> <div class="o_we_bg_filter" contenteditable="false"> </div> <div class="o_we_shape" contenteditable="false"> </div>`
    );
});
