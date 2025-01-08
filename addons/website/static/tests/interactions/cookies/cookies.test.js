import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { click, queryOne, waitFor } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

import { cookie } from "@web/core/browser/cookie";

setupInteractionWhiteList(["website.cookies_bar", "website.cookies_approval", "website.cookies_warning"]);

describe.current.tags("interaction_dev");

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

const cookiesApprovalTemplate = `
    <div data-need-cookies-approval="true">
        <iframe src="about:blank" data-nocookie-src="/"></iframe>
    </div>
`;

test("consent for optional cookies not given if click on #cookies-consent-essential", async () => {
    const { core } = await startInteractions(cookiesBarTemplate);
    expect(core.interactions).toHaveLength(1);
    expect(cookie.get("website_cookies_bar")).toBe(undefined);
    const cookiesBarEl = queryOne("#website_cookies_bar .modal");
    await waitFor(cookiesBarEl, { visible: true });
    await click("#cookies-consent-essential");
    expect(cookiesBarEl).not.toBeVisible();
    expect(cookie.get("website_cookies_bar")).toBe('{"required": true, "optional": false}');
});

test("consent for optional cookies not given if no click", async () => {
    const { core } = await startInteractions(cookiesBarTemplate);
    expect(core.interactions).toHaveLength(1);
    expect(cookie.get("website_cookies_bar")).toBe(undefined);
    const cookiesBarEl = queryOne("#website_cookies_bar .modal");
    await waitFor(cookiesBarEl, { visible: true });
    await advanceTime(1000000);
    expect(cookiesBarEl).toBeVisible();
    core.stopInteractions();
    expect(cookiesBarEl).not.toBeVisible();
    expect(cookie.get("website_cookies_bar")).toBe(undefined);
});

test("consent for optional cookies given if click on #cookies-consent-all", async () => {
    const { core } = await startInteractions(cookiesBarTemplate);
    expect(core.interactions).toHaveLength(1);
    expect(cookie.get("website_cookies_bar")).toBe(undefined);
    const cookiesBarEl = queryOne("#website_cookies_bar .modal");
    await waitFor(cookiesBarEl, { visible: true });
    expect(cookiesBarEl).toBeVisible();
    await click("#cookies-consent-all");
    expect(cookiesBarEl).not.toBeVisible();
    expect(cookie.get("website_cookies_bar")).toBe('{"required": true, "optional": true}');
})

test("show warning instead of iframe if no consent", async () => {
    const { core } = await startInteractions(cookiesApprovalTemplate);
    expect(core.interactions).toHaveLength(2);
    const iframeEl = queryOne("iframe");
    expect(iframeEl).toHaveClass("d-none");
    expect(iframeEl.nextElementSibling).not.toBe(null);
    const warningEl = queryOne(".o_no_optional_cookie");
    expect(iframeEl.nextElementSibling).toBe(warningEl);
});

test("show cookies bar after clicking on warning", async () => {
    const { core } = await startInteractions(`
        <div>
            ${cookiesApprovalTemplate}
            ${cookiesBarTemplate}
        </div>
    `);
    expect(core.interactions).toHaveLength(3);
    const cookiesBarEl = queryOne("#website_cookies_bar .modal");
    expect("iframe").toHaveAttribute("src", "about:blank");
    expect("iframe").toHaveAttribute("data-nocookie-src", "/");
    await waitFor(cookiesBarEl, { visible: true });
    await click("#cookies-consent-essential");
    expect(cookiesBarEl).not.toBeVisible();
    expect("iframe").not.toBeVisible();
    expect(".o_no_optional_cookie").toBeVisible();
    expect("iframe").toHaveAttribute("src", "about:blank");
    expect("iframe").toHaveAttribute("data-nocookie-src", "/");
    await click(".o_no_optional_cookie");
    expect(cookiesBarEl).toBeVisible();
});

test("remove warning, show and update iframe src after accepting cookies", async () => {
    const { core } = await startInteractions(`
        <div>
            ${cookiesApprovalTemplate}
            ${cookiesBarTemplate}
        </div>
    `);
    expect(core.interactions).toHaveLength(3);
    expect("iframe").toHaveAttribute("src", "about:blank");
    expect("iframe").toHaveAttribute("data-nocookie-src", "/");
    await waitFor("#website_cookies_bar .modal", { visible: true });
    await click("#cookies-consent-all");
    expect(".o_no_optional_cookie").not.toBeVisible();
    expect("iframe").toBeVisible();
    expect("iframe").toHaveAttribute("src", "/");
    expect("iframe").not.toHaveAttribute("data-nocookie-src");
    expect("[data-need-cookies-approval]").not.toHaveAttribute("data-need-cookies-approval");
});
