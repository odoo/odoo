import { describe, expect, test } from "@odoo/hoot";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { switchToEditMode } from "../../helpers";
import { tick } from "@odoo/hoot-dom";

describe.current.tags("interaction_dev");
setupInteractionWhiteList("website.countdown");

const getTemplate = function (options = { endAction: "nothing", endTime: "98765432100" }) {
    return `
        <div style="background-color: white;">
            <section class="s_countdown pt48 pb48 ${
                options.endAction === "message_no_countdown" ? "hide-countdown" : ""
            }"
            data-display="dhms"
            data-end-action="${options.endAction}"
            data-size="175"
            data-layout="circle"
            data-layout-background="none"
            data-progress-bar-style="surrounded"
            data-progress-bar-weight="thin"
            id="countdown-section"
            data-text-color="o-color-1"
            data-layout-background-color="400"
            data-progress-bar-color="o-color-1"
            data-end-time="${options.endTime}">
                <div class="container">
                    <div class="s_countdown_canvas_wrapper"
                    style="
                        display: flex;
                        justify-content: center;
                        align-items: center;">
                    </div>
                </div>
                ${["message", "message_no_countdown"].includes(options.endAction) ? endMessage : ""}
            </section>
        </div>
    `;
};

const endMessage = `
    <div class="s_countdown_end_message d-none">
        <div class="oe_structure">
            <section class="s_picture pt64 pb64" data-snippet="s_picture">
                <div class="container">
                    <h2 style="text-align: center;">Happy Odoo Anniversary!</h2>
                    <p style="text-align: center;">As promised, we will offer 4 free tickets to our next summit.<br/>Visit our Facebook page to know if you are one of the lucky winners.</p>
                    <div class="row s_nb_column_fixed">
                        <div class="col-lg-12" style="text-align: center;">
                            <figure class="figure">
                                <img src="/web/image/website.library_image_18" class="figure-img img-fluid rounded" alt="Countdown is over - Firework"/>
                            </figure>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    </div>
`;

test("past date: end message is not shown and countdown remains visible", async () => {
    const { core } = await startInteractions(
        getTemplate({ endAction: "message_no_countdown", endTime: "1" }),
        { waitForStart: true, editMode: true }
    );
    await switchToEditMode(core);

    await tick();
    expect(".s_countdown_end_message:not(.d-none)").toHaveCount(0);
    expect(".s_countdown_canvas_flex canvas:not(.d-none)").toHaveCount(4);
});
