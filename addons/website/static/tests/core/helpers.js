import { getFixture, after } from "@odoo/hoot";
import {
    clearRegistry,
    makeMockEnv,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { registry } from "@web/core/registry";
import { buildEditableInteractions } from "@web/legacy/js/public/interaction_util";

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
    options = { waitForStart: true, editMode: false, translateMode: false },
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
    if (options.translateMode) {
        core.el.closest("html").dataset.edit_translations = "1";
    }
    if (options.editMode) {
        core.stopInteractions();
        const builders = registry.category("website.editable_active_elements_builders").getEntries();
        for (const [key, builder] of builders) {
            if (activeInteractions && !activeInteractions.includes(key)) {
                builder.isAbstract = true;
            }
        }
        const editableInteractions = buildEditableInteractions(builders.map((builder) => builder[1]));
        core.activate(editableInteractions);
    }
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
    const width = (window.innerWidth || document.documentElement.clientWidth);
    const height = (window.innerHeight || document.documentElement.clientHeight);
    return (
        Math.round(rect.top) >= 0
        && Math.round(rect.left) >= 0
        && Math.round(rect.right) <= width
        && Math.round(rect.bottom) <= height
    );
}

export function isElementVerticallyInViewportOf(el, scrollEl) {
    const rect = el.getBoundingClientRect();
    return rect.top <= scrollEl.clientHeight && rect.bottom >= 0;
}
