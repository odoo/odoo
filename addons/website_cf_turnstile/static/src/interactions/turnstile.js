import { session } from "@web/session";


export class TurnStile {
    constructor(action, selector) {
        const cf = new URLSearchParams(window.location.search).get("cf");
        const mode = cf == "show" ? "always" : "interaction-only";
        const turnstileEl = document.createElement("div");
        turnstileEl.className = "s_turnstile cf-turnstile";
        turnstileEl.dataset.action = action;
        turnstileEl.dataset.appearance = mode;
        turnstileEl.dataset.responseFieldName = "turnstile_captcha";
        turnstileEl.dataset.sitekey = session.turnstile_site_key;
        turnstileEl.dataset.errorCallback = "throwTurnstileError";
        turnstileEl.dataset.beforeInteractiveCallback = "turnstileBeforeInteractive";
        turnstileEl.dataset.afterInteractiveCallback = "turnstileAfterInteractive";

        const script1El = document.createElement("script");
        script1El.className = "s_turnstile";
        script1El.textContent = `
            // Rethrow the error, or we only will catch a "Script error" without any info
            // because of the script api.js originating from a different domain.
            function throwTurnstileError(code) {
                const error = new Error("Turnstile Error");
                error.code = code;
                throw error;
            }
            function turnstileBeforeInteractive() {
                const btnEl = document.querySelector("${selector}");
                if (btnEl && !btnEl.classList.contains("disabled")) {
                    btnEl.classList.add("disabled", "cf_form_disabled");
                }
            }
            function turnstileAfterInteractive() {
                const btnEl = document.querySelector("${selector}");
                if (btnEl && btnEl.classList.contains("cf_form_disabled")) {
                    btnEl.classList.remove("disabled", "cf_form_disabled");
                }
            }
        `;

        const script2El = document.createElement("script");
        script2El.className = "s_turnstile";
        script2El.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";

        this.turnstileEl = turnstileEl;
        this.script1El = script1El;
        this.script2El = script2El;
    }

    /**
     * Remove potential existing loaded script/token
     *
     * @param {HTMLElement} el
     */
    static clean(el) {
        const turnstileEls = el.querySelectorAll(".s_turnstile");
        turnstileEls.forEach(element => element.remove());
    }
}
