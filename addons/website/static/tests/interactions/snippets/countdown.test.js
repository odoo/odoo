import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryAll, queryOne, tick } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

setupInteractionWhiteList("website.countdown");

describe.current.tags("interaction_dev");

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
                            <figure class="figure w-100">
                                <img src="/web/image/website.library_image_18" class="figure-img img-fluid rounded" alt="Countdown is over - Firework"/>
                            </figure>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    </div>
`;

const wasDataChanged = function (data1, data2, l) {
    for (let i = 0; i < l; i++) {
        if (Math.abs(data1[i] - data2[i]) > 1) {
            return true;
        }
    }
    return false;
};

test("countdown is started when there is an element .s_countdown", async () => {
    const { core } = await startInteractions(getTemplate());
    expect(core.interactions).toHaveLength(1);
});

/**
 * This test use 2 timestamps because in the rare case when the
 * countdown is at xx:xx:00, the next frame will update the multiple
 * canvases, including the hours one. It won't happen a second time.
 * We compare the canvases twice to prevent the issue.
 */
test("[time] countdown display is updated correctly when time pass", async () => {
    await startInteractions(getTemplate());

    const canvasEls = queryAll("canvas");
    const canvasHours = canvasEls[1];
    const canvasSeconds = canvasEls[3];
    const canvasHoursCtx = canvasHours.getContext("2d");
    const canvasSecondsCtx = canvasSeconds.getContext("2d");

    // time T
    const data1Hours = canvasHoursCtx.getImageData(
        0,
        0,
        canvasHours.width,
        canvasHours.height
    ).data;
    const data1Seconds = canvasSecondsCtx.getImageData(
        0,
        0,
        canvasSeconds.width,
        canvasSeconds.height
    ).data;

    // time T + 1s
    await advanceTime(1000);
    const data2Hours = canvasHoursCtx.getImageData(
        0,
        0,
        canvasHours.width,
        canvasHours.height
    ).data;
    const data2Seconds = canvasSecondsCtx.getImageData(
        0,
        0,
        canvasSeconds.width,
        canvasSeconds.height
    ).data;

    // time T + 2s
    await advanceTime(1000);
    const data3Hours = canvasHoursCtx.getImageData(
        0,
        0,
        canvasHours.width,
        canvasHours.height
    ).data;
    const data3Seconds = canvasSecondsCtx.getImageData(
        0,
        0,
        canvasSeconds.width,
        canvasSeconds.height
    ).data;

    // Check that the data are not empty & the same size

    const dataHoursLength = data1Hours.length;
    const dataSecondsLength = data1Seconds.length;
    expect(dataSecondsLength).toBe(dataHoursLength);
    expect(dataSecondsLength).not.toBe(0);

    // Compare data

    const hoursUpdate12 = wasDataChanged(data1Hours, data2Hours, dataHoursLength);
    const hoursUpdate23 = wasDataChanged(data2Hours, data3Hours, dataHoursLength);
    const secondsUpdate12 = wasDataChanged(data1Seconds, data2Seconds, dataSecondsLength);
    const secondsUpdate23 = wasDataChanged(data2Seconds, data3Seconds, dataSecondsLength);

    // Hour canvas must not have changed twice
    expect(hoursUpdate12 && hoursUpdate23).toBe(false);

    // Second canvas must have changed twice
    expect(secondsUpdate12 && secondsUpdate23).toBe(true);
});

test("countdown is stopped correctly", async () => {
    const { core } = await startInteractions(getTemplate());
    await advanceTime(0);
    expect(queryAll(".s_countdown_canvas_flex")).toHaveLength(4);
    core.stopInteractions();
    expect(queryOne(".s_countdown_canvas_wrapper")).not.toBe(null);
    expect(queryAll(".s_countdown_canvas_flex")).toHaveLength(0);
    expect(queryAll(".s_countdown_end_message")).toHaveLength(0);
    expect(queryAll(".s_countdown_text_wrapper")).toHaveLength(0);
    expect(queryAll(".s_countdown_end_redirect_message")).toHaveLength(0);
});

test("Countdown snippet exists, when the colors are not defined", async () => {
    const countdownEl = `<section class="s_countdown pt48 pb48"
            data-display="dhms"
            data-end-action="nothing"
            data-size="175"
            data-layout="circle"
            data-layout-background="none"
            data-progress-bar-style="surrounded"
            data-progress-bar-weight="thin"
            id="countdown-section"
            data-end-time="1749351790.469224">
                <div class="container">
                    <div class="s_countdown_canvas_wrapper"
                    style="
                        display: flex;
                        justify-content: center;
                        align-items: center;">
                    </div>
                </div>
            </section>`;
    const { core } = await startInteractions(countdownEl);
    expect(".o_error_dialog").toHaveCount(0);
    expect(core.interactions).toHaveLength(1);
});

test("past date: redirect end message is shown", async () => {
    await startInteractions(getTemplate({ endAction: "redirect", endTime: 1 }));
    await tick();
    expect(".s_countdown_end_redirect_message").toHaveCount(1);
});

test("past date: end message is shown", async () => {
    await startInteractions(getTemplate({ endAction: "message", endTime: 1 }));
    await tick();
    expect(".s_countdown_end_message:not(.d-none)").toHaveCount(1);
    expect(".s_countdown_canvas_flex canvas:not(.d-none)").toHaveCount(4);
});

test("past date: end message is shown without countdown", async () => {
    await startInteractions(getTemplate({ endAction: "message_no_countdown", endTime: 1 }));
    await tick();
    expect(".s_countdown_end_message:not(.d-none)").toHaveCount(1);
    expect(".s_countdown_canvas_flex canvas:not(.d-none)").toHaveCount(0);
});
