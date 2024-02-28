/** @odoo-module */

import tour from 'web_tour.tour';

const testUrl = '/test_client_action_redirect';

const goToFrontendSteps = [{
    content: "Go to the frontend",
    trigger: 'body',
    run: () => {
        window.location.href = testUrl;
    },
}, {
    content: "Check we are in the frontend",
    trigger: 'body:not(:has(.o_website_preview)) #test_contact_FE',
    run: () => null, // it's a check
}];
const goToBackendSteps = [{
    content: "Go to the backend",
    trigger: 'body',
    run: () => {
        window.location.href = `/@${testUrl}`;
    },
}, {
    content: "Check we are in the backend",
    trigger: '.o_website_preview',
    run: () => null, // it's a check
}];
const checkEditorSteps = [{
    content: "Check that the editor is loaded",
    trigger: 'iframe body.editor_enable',
    timeout: 30000,
    run: () => null, // it's a check
}, {
    content: "exit edit mode",
    trigger: '.o_we_website_top_actions button.btn-primary:contains("Save")',
}, {
    content: "wait for editor to close",
    trigger: 'iframe body:not(.editor_enable)',
    run: () => null, // It's a check
}];

tour.register('client_action_redirect', {
    test: true,
    url: testUrl,
},
[
    // Case 1: From frontend, click on `enable_editor=1` link without `/@/` in it
    ...goToFrontendSteps,
    {
        content: "Click on the link to frontend",
        trigger: '#test_contact_FE',
    },
    ...checkEditorSteps,

    // Case 2: From frontend, click on `enable_editor=1` link with `/@/` in it
    ...goToFrontendSteps,
    {
        content: "Click on the link to backend",
        trigger: '#test_contact_BE',
    },
    ...checkEditorSteps,

    // Case 3: From backend, click on `enable_editor=1` link without `/@/` in it
    // TODO: This will be fixed in another fix related to the listening of the
    //       URL changes from the client action.
    // ...goToBackendSteps,
    // {
    //     content: "Click on the link to frontend (2)",
    //     trigger: 'iframe #test_contact_FR',
    // },
    // ...checkEditorSteps,

    // Case 4: From backend, click on `enable_editor=1` link with `/@/` in it
    ...goToBackendSteps,
    {
        content: "Click on the link to backend (2)",
        trigger: 'iframe #test_contact_BE',
    },
    ...checkEditorSteps,
]);
