import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";

setupInteractionWhiteList("website.countdown");

describe.current.tags("interaction_dev");

const getTemplate = function (options = {}) {
    return `
        <div style="background-color: white;">
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
            data-end-time="12345678900">
                <div class="container">
                    <div class="s_countdown_canvas_wrapper"
                    style="
                        display: flex;
                        justify-content: center;
                        align-items: center;">
                    </div>
                </div>
            </section>
        </div>
    `
};

const wasDataChanged = function (data1, data2, l) {
    for (let i = 0; i < l; i++) {
        if (Math.abs(data1[i] - data2[i]) > 1) {
            return true;
        }
    }
    return false;
}

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
    const { el } = await startInteractions(getTemplate());

    const canvasEls = el.querySelectorAll('canvas');
    const canvasHours = canvasEls[1];
    const canvasSeconds = canvasEls[3];
    const canvasHoursCtx = canvasHours.getContext('2d');
    const canvasSecondsCtx = canvasSeconds.getContext('2d');

    // time T
    const data1Hours = canvasHoursCtx.getImageData(0, 0, canvasHours.width, canvasHours.height).data;
    const data1Seconds = canvasSecondsCtx.getImageData(0, 0, canvasSeconds.width, canvasSeconds.height).data;

    // time T + 1s
    await advanceTime(1000);
    const data2Hours = canvasHoursCtx.getImageData(0, 0, canvasHours.width, canvasHours.height).data;
    const data2Seconds = canvasSecondsCtx.getImageData(0, 0, canvasSeconds.width, canvasSeconds.height).data;

    // time T + 2s
    await advanceTime(1000);
    const data3Hours = canvasHoursCtx.getImageData(0, 0, canvasHours.width, canvasHours.height).data;
    const data3Seconds = canvasSecondsCtx.getImageData(0, 0, canvasSeconds.width, canvasSeconds.height).data;

    // Check that the data are not empty & the same size

    const dataHoursLength = data1Hours.length;
    const dataSecondsLength = data1Seconds.length
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
    const { core, el } = await startInteractions(getTemplate());
    const wrapEl = el.querySelector(".s_countdown_canvas_wrapper");
    await advanceTime(0);
    expect(wrapEl.querySelectorAll(".s_countdown_canvas_flex")).toHaveLength(4);
    core.stopInteractions();
    expect(!!wrapEl).toBe(true);
    expect(wrapEl.querySelectorAll(".s_countdown_canvas_flex")).toHaveLength(0);
    expect(wrapEl.querySelectorAll(".s_countdown_end_message")).toHaveLength(0);
    expect(wrapEl.querySelectorAll(".s_countdown_text_wrapper")).toHaveLength(0);
    expect(wrapEl.querySelectorAll(".s_countdown_end_redirect_message")).toHaveLength(0);
});
