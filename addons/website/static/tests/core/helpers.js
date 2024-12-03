import { getFixture, after } from "@odoo/hoot";
import {
    clearRegistry,
    makeMockEnv,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { registry } from "@web/core/registry";

let activeInteractions = null;
let elementRegistry = registry.category("website.active_elements");
let content = elementRegistry.content;

export function setupInteractionWhiteList(interactions) {
    if (typeof interactions === "string") {
        interactions = [interactions];
    }
    activeInteractions = interactions;
}

export async function startInteraction(I, html, options) {
    clearRegistry(elementRegistry);
    for (let Interaction of (Array.isArray(I) ? I : [I])) {
        elementRegistry.add(Interaction.name, Interaction);

    }
    return startInteractions(html, options);
}

export async function startInteractions(
    html,
    options = { waitForStart: true },
) {
    defineMailModels();
    const fixture = getFixture();
    if (!html.includes("wrapwrap")) {
        html = `<div id="wrapwrap">${html}</div>`;
    }
    fixture.innerHTML = html;
    if (activeInteractions) {
        clearRegistry(elementRegistry);
        for (const name of activeInteractions) {
            if (name in content) {
                elementRegistry.add(name, content[name][1]);
            } else {
                throw new Error(`White-listed Interaction does not exist: ${name}.`);
            }
        }
    }
    const env = await makeMockEnv();
    const core = env.services.website_core;
    if (options.waitForStart) {
        await core.isReady;
    }
    after(() => core.stopInteractions());

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
        rect.bottom <=
            (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <=
            (window.innerWidth || document.documentElement.clientWidth)
    );
}

export function isElementVerticallyInViewportOf(el, scrollEl) {
    const rect = el.getBoundingClientRect();
    return rect.top <= scrollEl.clientHeight && rect.bottom >= 0;
}
