import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { describe, expect, test, microTick, freezeTime } from "@odoo/hoot";
import { queryAll, queryOne, tick } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { startInteractionsWithSnippet } from "../helpers";
import { processCountdownHTML } from "./helpers";

setupInteractionWhiteList("website.countdown");

describe.current.tags("interaction_dev");

const wasDataChanged = function (data1, data2, l) {
    for (let i = 0; i < l; i++) {
        if (Math.abs(data1[i] - data2[i]) > 1) {
            return true;
        }
    }
    return false;
};

test("countdown is started when there is an element .s_countdown", async () => {
    const { core } = await startInteractionsWithSnippet("s_countdown");
    expect(core.interactions).toHaveLength(1);
});

/**
 * This test use 2 timestamps because in the rare case when the
 * countdown is at xx:xx:00, the next frame will update the multiple
 * canvases, including the hours one. It won't happen a second time.
 * We compare the canvases twice to prevent the issue.
 */
test("[time] countdown display is updated correctly when time pass", async () => {
    freezeTime();
    await startInteractionsWithSnippet("s_countdown");

    // Countdown renders at the setup of the interaction, and then at the start
    // of the next second, so we advance time here to properly have a new render
    // every second.
    await advanceTime(1000);
    await microTick();

    const canvasEls = queryAll("canvas");
    const canvasHours = canvasEls[1];
    const canvasSeconds = canvasEls[3];
    const canvasHoursCtx = canvasHours.getContext("2d");
    const canvasSecondsCtx = canvasSeconds.getContext("2d");

    const getHours = () =>
        canvasHoursCtx.getImageData(0, 0, canvasHours.width, canvasHours.height).data;
    const getSeconds = () =>
        canvasSecondsCtx.getImageData(0, 0, canvasSeconds.width, canvasSeconds.height).data;

    // time T
    const data1Hours = getHours();
    const data1Seconds = getSeconds();

    // time T + 1s
    await advanceTime(1000);
    await microTick();
    const data2Hours = getHours();
    const data2Seconds = getSeconds();

    // time T + 2s
    await advanceTime(1000);
    await microTick();
    const data3Hours = getHours();
    const data3Seconds = getSeconds();

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
    const { core } = await startInteractionsWithSnippet("s_countdown");
    await advanceTime(0);
    expect(queryAll(".s_countdown_canvas_flex")).toHaveLength(4);
    core.stopInteractions();
    expect(queryOne(".s_countdown_wrapper")).not.toBe(null);
    expect(queryAll(".s_countdown_canvas_flex")).toHaveLength(0);
    expect(queryAll(".s_countdown_end_message")).toHaveLength(0);
    expect(queryAll(".s_countdown_text_wrapper")).toHaveLength(0);
    expect(queryAll(".s_countdown_end_redirect_message")).toHaveLength(0);
});

test("Countdown snippet exists, when the colors are not defined", async () => {
    const { core } = await startInteractionsWithSnippet("s_countdown", {
        processHTML: (html) => {
            const countdownEl = html.querySelector("[data-snippet='s_countdown']");
            delete countdownEl.textColor;
            delete countdownEl.layoutBackgroundColor;
            delete countdownEl.progressBarColor;
        },
    });
    expect(".o_error_dialog").toHaveCount(0);
    expect(core.interactions).toHaveLength(1);
});

test("past date: redirect end message is shown", async () => {
    await startInteractionsWithSnippet("s_countdown", {
        processHTML: processCountdownHTML({ endAction: "redirect", endTime: 1 }),
    });
    await tick();
    expect(".s_countdown_end_redirect_message").toHaveCount(1);
});

test("past date: end message is shown", async () => {
    await startInteractionsWithSnippet("s_countdown", {
        processHTML: processCountdownHTML({ endAction: "message", endTime: 1 }),
    });
    await tick();
    expect(".s_countdown_end_message:not(.d-none)").toHaveCount(1);
    expect(".s_countdown_canvas_flex canvas:not(.d-none)").toHaveCount(4);
});

test("past date: end message is shown without countdown", async () => {
    await startInteractionsWithSnippet("s_countdown", {
        processHTML: processCountdownHTML({ endAction: "message_no_countdown", endTime: 1 }),
    });
    await tick();
    expect(".s_countdown_end_message:not(.d-none)").toHaveCount(1);
    expect(".s_countdown_canvas_flex canvas:not(.d-none)").toHaveCount(0);
});

// TODO: remove in 23.0
test("old countdown is supported", async () => {
    const template = `
        <section class="s_countdown pt48 pb48"
            data-display="dhms"
            data-end-action="nothing"
            data-size="175"
            data-layout="circle"
            data-layout-background="none"
            data-progress-bar-style="surrounded"
            data-progress-bar-weight="thin"
            id="countdown-section"
            data-text-color="o-color-1"
            data-layout-background-color="400"
            data-progress-bar-color="o-color-1"
            data-end-time="98765432100">
                <div class="container">
                    <div class="s_countdown_canvas_wrapper"
                        style="
                            display: flex;
                            justify-content: center;
                            align-items: center;">
                    </div>
                </div>
            </section>
        </div>`;
    const { core } = await startInteractions(template);
    expect(core.interactions).toHaveLength(1);
    expect(".s_countdown_canvas_flex canvas:not(.d-none)").toHaveCount(4);
});
