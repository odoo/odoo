import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    getDragMoveHelper,
    setupHTMLBuilder,
    waitForEndOfOperation,
} from "@html_builder/../tests/helpers";

const dropzoneSelectors = {
    selector: "section",
    dropNear: "section",
};

test("Drag and drop basic test", async () => {
    await setupHTMLBuilder(
        `
            <section class="section-1"><div><p>Text 1</p></div></section>
            <section class="section-2"><div><p>Text 2</p></div></section>
        `,
        { dropzoneSelectors }
    );

    await contains(":iframe section.section-1").click();
    expect(".overlay .o_overlay_options .o_move_handle.o_draggable").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(".o_overlay_options .o_move_handle").drag();
    expect(":iframe .oe_drop_zone").toHaveCount(2);
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    await moveTo(":iframe .oe_drop_zone:nth-child(3)");
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveClass("invisible");
    expect(":iframe section.section-1:nth-child(4)").toHaveCount(1);

    await drop(getDragMoveHelper());
    expect(":iframe .oe_drop_zone").toHaveCount(0);
    expect(":iframe section.section-1:nth-child(2)").toHaveCount(1);
    await waitForEndOfOperation();
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});
