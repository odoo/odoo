import { describe, expect, test } from "@odoo/hoot";

import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
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
}

const getCommonLength = function (data1, data2, data3) {
    const length1 = data1.length;
    const length2 = data2.length;
    const length3 = data3.length;
    if (length1 == length2 && length2 == length3) {
        return length1;
    } else {
        return 0;
    }
}

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
    expect(core.interactions.length).toBe(1);
});

/**
 * This test use 2 timestamps because in the rare case when the
 * countdown is at xx:xx:00, the next frame will update the multiple
 * canvases, including the hours one. It won't happen a second time.
 * We compare the canvases twice to prevent the issue.
 */
test("[time] countdown display is updated correctly when time pass", async () => {
    const { el } = await startInteractions(getTemplate());

    // time T

    const canvas1Els = el.querySelectorAll('canvas');
    const canvas1Hours = canvas1Els[1];
    const data1Hours = canvas1Hours.getContext('2d').getImageData(0, 0, canvas1Hours.width, canvas1Hours.height).data;
    const canvas1Seconds = canvas1Els[3];
    const data1Seconds = canvas1Seconds.getContext('2d').getImageData(0, 0, canvas1Seconds.width, canvas1Seconds.height).data;

    await advanceTime(1000);

    // time T + 1s

    const canvas2Els = el.querySelectorAll('canvas');
    const canvas2Hours = canvas2Els[1];
    const data2Hours = canvas2Hours.getContext('2d').getImageData(0, 0, canvas2Hours.width, canvas2Hours.height).data;
    const canvas2Seconds = canvas2Els[3];
    const data2Seconds = canvas2Seconds.getContext('2d').getImageData(0, 0, canvas2Seconds.width, canvas2Seconds.height).data;

    await advanceTime(1000);

    // time T + 2s

    const canvas3Els = el.querySelectorAll('canvas');
    const canvas3Hours = canvas3Els[1];
    const data3Hours = canvas3Hours.getContext('2d').getImageData(0, 0, canvas3Hours.width, canvas3Hours.height).data;
    const canvas3Seconds = canvas3Els[3];
    const data3Seconds = canvas3Seconds.getContext('2d').getImageData(0, 0, canvas3Seconds.width, canvas3Seconds.height).data;

    // Check data size and get common length

    const dataHoursLength = getCommonLength(data1Hours, data2Hours, data3Hours)
    expect(dataHoursLength).not.toBe(0);

    const dataSecondsLength = getCommonLength(data1Seconds, data2Seconds, data3Seconds)
    expect(dataSecondsLength).not.toBe(0);

    // Compare data

    const hoursUpdate12 = wasDataChanged(data1Hours, data2Hours, dataHoursLength);
    const hoursUpdate23 = wasDataChanged(data2Hours, data3Hours, dataHoursLength);
    const secondsUpdate12 = wasDataChanged(data1Seconds, data2Seconds, dataHoursLength);
    const secondsUpdate23 = wasDataChanged(data2Seconds, data3Seconds, dataHoursLength);

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
