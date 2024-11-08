import { getFixture } from "@odoo/hoot";
import { clearRegistry, makeMockEnv, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { registry } from "@web/core/registry";
import { isInViewPort } from "@odoo/hoot-dom";;

defineMailModels();

let activeInteractions = null;
let elementRegistry = registry.category("website.active_elements");
let content = elementRegistry.content;

export function setupInteractionWhiteList(interactions) {
    if (typeof interactions === "string") {
        interactions = [interactions];
    }
    activeInteractions = interactions;
}

export async function startInteraction(I, html) {
    clearRegistry(elementRegistry);
    elementRegistry.add(I.constructor.name, I);
    return startInteractions(html);
}

export async function startInteractions(html) {
    const fixture = getFixture();
    if (!html.includes("wrapwrap")) {
        html = `<div id="wrapwrap">${html}</div>`;
    }
    fixture.innerHTML = html;
    if (activeInteractions) {
        clearRegistry(elementRegistry);
        for (let name of activeInteractions) {
            if (name in content) {
                elementRegistry.add(name, content[name][1]);
            }
        }
    }
    const env = await makeMockEnv();
    const core = env.services.website_core;
    return {
        el: fixture,
        core,
    };
}

export function mockSendRequests() {
    const requests = [];
    patchWithCleanup(HTMLFormElement.prototype, {
        submit: function () {
            requests.push({
                url: this.getAttribute("action"),
                method: this.getAttribute("method"),
            });
        },
    });
    return requests;
}

export function isElementInViewport(el) {
    const rect = el.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

export function isElementVerticallyInViewportOf(el, scrollEl) {
    const rect = el.getBoundingClientRect();
    return (
        rect.top <= scrollEl.clientHeight &&
        rect.bottom >= 0
    );
}
