/** @odoo-module **/
import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';
import { stepUtils } from "@web_tour/tour_service/tour_utils";

/**
 * The purpose of these tours is to check the systray visibility:
 *
 * - as an administrator
 * - as a restricted editor with "tester" right
 * - as a restricted editor without "tester" right
 * - as a "tester" who is not a restricted editor
 * - as an unrelated user (neither "tester" nor restricted editor)
 */

const canPublish = () => [{
    content: "Publish",
    trigger: '.o_menu_systray .o_menu_systray_item:contains("Unpublished")',
    run: "click",
}, {
    content: "Wait for Publish",
    trigger: '.o_menu_systray .o_menu_systray_item:contains("Published"):not([data-processing])',
}, {
    content: "Unpublish",
    trigger: '.o_menu_systray .o_menu_systray_item:contains("Published")',
    run: "click",
}, {
    content: "Wait for Unpublish",
    trigger: '.o_menu_systray .o_menu_systray_item:contains("Unpublished"):not([data-processing])',
}];

const cannotPublish = () => [{
    content: "Check has no Publish/Unpublish",
    trigger: '.o_menu_systray:not(:has(.o_menu_systray_item:contains("ublished")))',
}];

const canToggleMobilePreview = () => [{
    content: "Enable mobile preview",
    trigger: '.o_menu_systray .o_menu_systray_item.o_mobile_preview:not(.o_mobile_preview_active) span',
    run: "click",
}, {
    content: "Disable mobile preview",
    trigger: '.o_menu_systray .o_menu_systray_item.o_mobile_preview.o_mobile_preview_active span',
    run: "click",
}];

const cannotToggleMobilePreview = () => [{
    content: 'Enable mobile preview',
    trigger: '.o_menu_systray:not(:has(.o_menu_systray_item.o_mobile_preview))',
}];

// For non-website users, switching across website only works if the domains are
// specified. Within the scope of test tours, this cannot be achieved.
const canSwitchWebsiteNoCheck = () => [{
    content: 'Open website switcher',
    trigger: '.o_menu_systray .o_menu_systray_item.o_website_switcher_container .dropdown-toggle:contains("My Website"):not(:contains("My Website 2"))',
    run: "click",
}, {
    content: 'Can switch to other website',
    trigger: '.o-dropdown--menu .dropdown-item:contains("Other")',
}];


const canSwitchWebsite = () => [{
    content: "Open website switcher",
    trigger: '.o_menu_systray .o_menu_systray_item.o_website_switcher_container .dropdown-toggle:contains("My Website"):not(:contains("My Website 2"))',
    run: "click",
}, {
    content: "Switch to other website",
    trigger: '.o-dropdown--menu .dropdown-item:contains("Other")',
    run: "click",
}, {
    content: "Wait for other website",
    trigger: ':iframe  body:contains("Test Model") div:contains("Other")',
}];

const canAddNewContent = () => [{
    content: "Open +New content",
    trigger: '.o_menu_systray .o_menu_systray_item.o_new_content_container',
    run: "click",
}, {
    content: "Close +New content",
    trigger: '#o_new_content_menu_choices',
    run: "click",
}];

const cannotAddNewContent = () => [{
    content: 'No +New content',
    trigger: '.o_menu_systray:not(:has(.o_menu_systray_item.o_new_content_container))',
}];

const canEditInBackEnd = () => [{
    content: "Edit in backend",
    trigger: '.o_menu_systray .o_website_edit_in_backend a',
    run: "click",
}, {
    content: "Check that the form is editable",
    trigger: '.o_form_view_container .o_form_editable',
}, {
    content: "Return to website",
    trigger: '.o-form-buttonbox .fa-globe',
    run: "click",
}];

const canViewInBackEnd = () => [{
    content: "Go to backend",
    trigger: '.o_menu_systray .o_website_edit_in_backend a',
    run: "click",
}, {
    content: "Check that the form is read-only",
    trigger: '.o_form_view_container .o_form_readonly',
}, {
    content: "Return to website",
    trigger: '.o-form-buttonbox .fa-globe',
    run: "click",
}];

const canEdit = () => [
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Click on name",
        trigger: ':iframe span[data-oe-expression="test_model.name"][contenteditable="true"]',
        run: "click",
    }, {
        content: "Change name",
        trigger: ':iframe span[data-oe-expression="test_model.name"][contenteditable="true"]',
        run: "editor Better name",
    }, {
        content: "Check that field becomes dirty",
        trigger: ':iframe span[data-oe-expression="test_model.name"].o_dirty',
    },
    ...clickOnSave(),
    {
        content: "Check whether name is saved",
        trigger: ':iframe span[data-oe-expression="test_model.name"]:contains("Better name")',
    },
];

const cannotEdit = () => [stepUtils.waitIframeIsReady(), {
    content: "Check Edit is not available",
    trigger: '.o_menu_systray:not(:has(.o_edit_website_container))',
}];

const canEditButCannotChange = () => [
    ...clickOnEditAndWaitEditMode(),
    {
        content: 'Cannot change name',
        trigger: ':iframe main:not(:has([data-oe-expression])):contains("Test Model")',
    },
];

const register = (title, steps) => {
    registerWebsitePreviewTour(title, {
        url: "/test_model/1",
    }, steps);
};

register("test_systray_admin", () => [
    ...canPublish(),
    ...canToggleMobilePreview(),
    ...canSwitchWebsite(),
    ...canAddNewContent(),
    ...canEditInBackEnd(),
    ...canEdit(),
]);

register("test_systray_reditor_tester", () => [
    ...canPublish(),
    ...canToggleMobilePreview(),
    ...canSwitchWebsite(),
    ...canAddNewContent(),
    ...canEditInBackEnd(),
    ...canEdit(),
]);

register("test_systray_reditor_not_tester", () => [
    ...cannotPublish(),
    ...canToggleMobilePreview(),
    ...canSwitchWebsite(),
    ...canAddNewContent(),
    ...canViewInBackEnd(),
    ...canEditButCannotChange(),
]);

register("test_systray_not_reditor_tester", () => [
    ...canPublish(),
    ...cannotToggleMobilePreview(),
    ...canSwitchWebsiteNoCheck(),
    ...cannotAddNewContent(),
    ...canEditInBackEnd(),
    ...cannotEdit(),
]);

register("test_systray_not_reditor_not_tester", () => [
    ...cannotPublish(),
    ...cannotToggleMobilePreview(),
    ...canSwitchWebsiteNoCheck(),
    ...cannotAddNewContent(),
    ...canViewInBackEnd(),
    ...cannotEdit(),
    {
        trigger: ":iframe main:contains(test model)",
    },
]);
