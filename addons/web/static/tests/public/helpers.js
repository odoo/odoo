import { getFixture, after } from "@odoo/hoot";
import { clearRegistry, makeMockEnv, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

let activeInteractions = null;
const elementRegistry = registry.category("public.interactions");
const content = elementRegistry.content;

export function setupInteractionWhiteList(interactions) {
    if (typeof interactions === "string") {
        interactions = [interactions];
    }
    activeInteractions = interactions;
}

setupInteractionWhiteList.getWhiteList = () => activeInteractions;

export async function startInteraction(I, html, options) {
    clearRegistry(elementRegistry);
    for (const Interaction of Array.isArray(I) ? I : [I]) {
        elementRegistry.add(Interaction.name, Interaction);
    }
    return startInteractions(html, options);
}

export async function startInteractions(
    html,
    options = { waitForStart: true, editMode: false, translateMode: false }
) {
    if (odoo.loader.modules.has("@mail/../tests/mail_test_helpers")) {
        const { defineMailModels } = odoo.loader.modules.get("@mail/../tests/mail_test_helpers");
        defineMailModels();
    }
    const fixture = getFixture();
    if (!html.includes("wrapwrap")) {
        html = `<div id="wrapwrap">${html}</div>`;
    }
    fixture.innerHTML = html;
    if (options.translateMode) {
        fixture.closest("html").dataset.edit_translations = "1";
    }
    if (activeInteractions) {
        clearRegistry(elementRegistry);
        if (!options.editMode) {
            for (const name of activeInteractions) {
                if (name in content) {
                    elementRegistry.add(name, content[name][1]);
                } else {
                    throw new Error(`White-listed Interaction does not exist: ${name}.`);
                }
            }
        }
    }
    const env = await makeMockEnv();
    const core = env.services["public.interactions"];
    if (options.waitForStart) {
        await core.isReady;
    }
    after(() => {
        delete fixture.closest("html").dataset.edit_translations;
        core.stopInteractions();
    });

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
    const width = window.innerWidth || document.documentElement.clientWidth;
    const height = window.innerHeight || document.documentElement.clientHeight;
    return (
        Math.round(rect.top) >= 0 &&
        Math.round(rect.left) >= 0 &&
        Math.round(rect.right) <= width &&
        Math.round(rect.bottom) <= height
    );
}

export function isElementVerticallyInViewportOf(el, scrollEl) {
    const rect = el.getBoundingClientRect();
    return rect.top <= scrollEl.clientHeight && rect.bottom >= 0;
}
