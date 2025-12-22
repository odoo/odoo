/** @odoo-module */
import { delay } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";

const testUrl = '/test_client_action_redirect';

const goToFrontendSteps = [{
    content: "Go to the frontend",
    trigger: 'body',
    async run() {
        await delay(2000);
        window.location.assign(testUrl);
    },
    expectUnloadPage: true,
}, {
    content: "Check we are in the frontend",
    trigger: 'body:not(:has(.o_website_preview)) #test_contact_FE',
}];
const goToBackendSteps = [{
    content: "Go to the backend",
    trigger: 'body',
    async run() {
        await delay(2000);
        window.location.assign(`/@${testUrl}`);
    },
    expectUnloadPage: true,
}, {
    content: "Check we are in the backend",
    trigger: ".o_website_preview[data-view-xmlid='website.test_client_action_redirect'] :iframe",
}];
const checkEditorSteps = [{
    content: "Check that the editor is loaded",
    trigger: ':iframe body.editor_enable',
    timeout: 30000,
}, {
    content: "exit edit mode",
    trigger: "button[data-action=save]:enabled:contains(save)",
    run: "click",
    timeout: 30000,
}, {
    content: "wait for editor to close",
    trigger: ':iframe body:not(.editor_enable)',
}];

registry.category("web_tour.tours").add('client_action_redirect', {
    url: testUrl,
    steps: () => [
    // Case 1: From frontend, click on `enable_editor=1` link without `/@/` in it
    ...goToFrontendSteps,
    {
        content: "Click on the link to frontend",
        trigger: '#test_contact_FE',
        run: "click",
        expectUnloadPage: true,
    },
    ...checkEditorSteps,

    // Case 2: From frontend, click on `enable_editor=1` link with `/@/` in it
    ...goToFrontendSteps,
    {
        content: "Click on the link to backend",
        trigger: '#test_contact_BE',
        run: "click",
        expectUnloadPage: true,
    },
    ...checkEditorSteps,

    // Case 3: From backend, click on `enable_editor=1` link without `/@/` in it
    // TODO: This will be fixed in another fix related to the listening of the
    //       URL changes from the client action.
    // ...goToBackendSteps,
    // {
    //     content: "Click on the link to frontend (2)",
    //     trigger: ':iframe #test_contact_FR',
    // },
    // ...checkEditorSteps,

    // Case 4: From backend, click on `enable_editor=1` link with `/@/` in it
    ...goToBackendSteps,
    {
        content: "Click on the link to backend (2)",
        trigger: ':iframe #test_contact_BE',
        run: "click",
        expectUnloadPage: true,
    },
    ...checkEditorSteps,
]});
