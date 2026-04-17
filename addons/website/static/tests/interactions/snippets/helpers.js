import { advanceTime, animationFrame, scroll } from "@odoo/hoot-dom";
import { defineStyle } from "@web/../tests/web_test_helpers";

export async function endTransition() {
    // Ensure we finish the transition
    await animationFrame();
    // Ensure the class "o_transitioning" is removed
    await advanceTime(500);
}

/**
 * @param {any} core
 * @param {any} wrapwrap
 */
export async function setupTest(core, wrapwrap) {
    wrapwrap.style.height = "800px";
    wrapwrap.style.width = "100%";
    wrapwrap.style.overflow = "scroll";
    core.interactions[0].interaction.scrollingElement = wrapwrap;
    defineStyle(/* css */ `.hidden { display: none !important; }`);
    defineStyle(/* css */ `.h20 { height: 20px; }`);
    await endTransition();
}

/**
 * @param {Parameters<scroll>[0]} wrapwrapEl
 * @param {Parameters<scroll>[1]} target
 */
export async function simpleScroll(wrapwrapEl, target) {
    await scroll(wrapwrapEl, target, { scrollable: false });
    await endTransition();
}

/**
 * Scroll twice to correctly updates parameters used by onScroll handlers.
 * (cf. Headers)
 *
 * @param {Parameters<scroll>[0]} wrapwrapEl
 * @param {number} target
 * @param {number} source
 */
export async function doubleScroll(wrapwrapEl, target, source) {
    await scroll(wrapwrapEl, { y: source + (target > source ? 1 : -1) });
    await scroll(wrapwrapEl, { y: target });
    await endTransition();
}

export const formSelectXml = `
    <form data-model_name="mail.mail">
        <div data-name="Field" class="s_website_form_field s_website_form_custom" data-type="many2one" data-other-option-allowed="true" data-other-option-label="Other" data-other-option-placeholder="Other option...">
            <div class="row s_col_no_resize s_col_no_bgcolor">
                <label class="col-form-label col-sm-auto s_website_form_label" for="o291di1too21">
                    <span class="s_website_form_label_content">Form Select</span>
                </label>
                <div class="col-sm">
                    <select class="form-select s_website_form_input" name="Form Select" id="field1">
                        <option value="Option 1" id="o291di1too22">Option 1</option>
                    </select>
                </div>
            </div>
        </div>
    </form>
`;

const countdownEndMessage = `
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

export function processCountdownHTML({ endAction = "nothing", endTime = "98765432100" } = {}) {
    return (html) => {
        const countdownEl = html.querySelector("[data-snippet='s_countdown']");
        countdownEl.dataset.endAction = endAction;
        countdownEl.dataset.endTime = endTime;
        countdownEl.classList.toggle("hide-countdown", endAction === "message_no_countdown");
        if (["message", "message_no_countdown"].includes(endAction)) {
            countdownEl.insertAdjacentHTML("beforeend", countdownEndMessage);
        }
    };
}
