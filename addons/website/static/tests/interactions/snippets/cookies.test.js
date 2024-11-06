import { expect, test } from "@odoo/hoot";
import {click, isVisible, queryOne, waitFor } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { cookie } from "@web/core/browser/cookie";
import { startInteractions, setupInteractionWhiteList } from "../../core/helpers";

setupInteractionWhiteList(["website.cookies_bar", "website.cookies_approval", "website.cookies_warning"]);

const cookiesBarTemplate = `
    <div id="website_cookies_bar" class="s_popup o_snippet_invisible" data-name="Cookies Bar" data-vcss="001" data-invisible="1">
        <div class="modal s_popup_bottom s_popup_no_backdrop o_cookies_discrete modal_shown"
                style="display: none;"
                data-show-after="0"
                data-display="afterDelay"
                data-consents-duration="999"
                data-bs-focus="false"
                data-bs-backdrop="false"
                tabindex="-1"
                aria-modal="true" role="dialog">
            <div class="modal-dialog s_popup_size_full">
                <div class="modal-content oe_structure">
                    <section>
                        <div class="container">
                            <p>
                                <a href="#" id="cookies-consent-essential" role="button" class="js_close_popup btn btn-outline-primary">Only essentials</a>
                                <a href="#" id="cookies-consent-all" role="button" class="js_close_popup btn btn-outline-primary">I agree</a>
                            </p>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    </div>
`;

test("consent for optional cookies not given if click on #cookies-consent-essential", async () => {
    const { core } = await startInteractions(cookiesBarTemplate);
    expect(core.interactions.length).toBe(1);
    expect(cookie.get("website_cookies_bar")).toBe(undefined);
    const cookiesBarEl = queryOne("#website_cookies_bar .modal");
    const consentEssentialEl = queryOne("#cookies-consent-essential");
    await waitFor(cookiesBarEl, { visible: "true" });
    await click(consentEssentialEl);
    expect(isVisible(cookiesBarEl)).toBe(false);
    expect(cookie.get("website_cookies_bar")).toBe('{"required": true, "optional": false}');
});

test("consent for optional cookies not given if no click", async () => {
    const { core } = await startInteractions(cookiesBarTemplate);
    expect(core.interactions.length).toBe(1);
    expect(cookie.get("website_cookies_bar")).toBe(undefined);
    const cookiesBarEl = queryOne("#website_cookies_bar .modal");
    await waitFor(cookiesBarEl, { visible: "true" });
    await advanceTime(1000000);
    expect(isVisible(cookiesBarEl)).toBe(true);
    core.stopInteractions();
    expect(isVisible(cookiesBarEl)).toBe(false);
    expect(cookie.get("website_cookies_bar")).toBe(undefined);
});

test("consent for optional cookies given if click on #cookies-consent-all", async () => {
    const { core } = await startInteractions(cookiesBarTemplate);
    expect(core.interactions.length).toBe(1);
    expect(cookie.get("website_cookies_bar")).toBe(undefined);
    const cookiesBarEl = queryOne("#website_cookies_bar .modal");
    const consentAllEl = queryOne("#cookies-consent-all");
    await waitFor(cookiesBarEl, { visible: "true" });
    await click(consentAllEl);
    expect(isVisible(cookiesBarEl)).toBe(false);
    expect(cookie.get("website_cookies_bar")).toBe('{"required": true, "optional": true}');
})

test("show warning instead of iframe if no consent", async () => {
    const { core } = await startInteractions(`
        <div data-need-cookies-approval="true">
            <iframe src="about:blank" data-nocookie-src="/"></iframe>
        </div>
    `);
    expect(core.interactions.length).toBe(2);
    const iframeEl = queryOne("iframe");
    expect(iframeEl.className).toBe("d-none");
    expect(iframeEl.nextElementSibling).not.toBe(null);
    const warningEl = queryOne(".o_no_optional_cookie");
    expect(iframeEl.nextElementSibling).toBe(warningEl);
});

test("show cookies bar after clicking on warning", async () => {
    const { core } = await startInteractions(`
        <div>
            <div data-need-cookies-approval="true">
                <iframe src="about:blank" data-nocookie-src="/"></iframe>
            </div>
            ${cookiesBarTemplate}
        </div>
    `);
    expect(core.interactions.length).toBe(3);
    const iframeEl = queryOne("iframe");
    const warningEl = queryOne(".o_no_optional_cookie");
    const cookiesBarEl = queryOne("#website_cookies_bar .modal");
    const consentEssentialEl = queryOne("#cookies-consent-essential");
    expect(iframeEl.getAttribute("src")).toBe("about:blank");
    expect(iframeEl.dataset.nocookieSrc).toBe("/");
    await waitFor(cookiesBarEl, { visible: "true" });
    await click(consentEssentialEl);
    expect(isVisible(cookiesBarEl)).toBe(false);
    expect(isVisible(iframeEl)).toBe(false);
    expect(isVisible(warningEl)).toBe(true);
    expect(iframeEl.getAttribute("src")).toBe("about:blank");
    expect(iframeEl.dataset.nocookieSrc).toBe("/");
    await click(warningEl);
    expect(isVisible(cookiesBarEl)).toBe(true);
});

test("remove warning, show and update iframe src after accepting cookies", async () => {
    const { core } = await startInteractions(`
        <div>
            <div data-need-cookies-approval="true">
                <iframe src="about:blank" data-nocookie-src="/"></iframe>
            </div>
            ${cookiesBarTemplate}
        </div>
    `);
    expect(core.interactions.length).toBe(3);
    const containerEl = queryOne("[data-need-cookies-approval]");
    const iframeEl = queryOne("iframe");
    const warningEl = queryOne(".o_no_optional_cookie");
    const cookiesBarEl = queryOne("#website_cookies_bar .modal");
    const consentAllEl = queryOne("#cookies-consent-all");
    expect(iframeEl.getAttribute("src")).toBe("about:blank");
    expect(iframeEl.dataset.nocookieSrc).toBe("/");
    await waitFor(cookiesBarEl, { visible: "true" });
    await click(consentAllEl);
    expect(isVisible(warningEl)).toBe(false);
    expect(isVisible(iframeEl)).toBe(true);
    expect(iframeEl.getAttribute("src")).toBe("/");
    expect(iframeEl.dataset.nocookieSrc).toBe(undefined);
    expect(containerEl.dataset.needCookiesApproval).toBe(undefined);
});
