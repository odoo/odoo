/** @odoo-module **/
import wTourUtils from '@website/js/tours/tour_utils';

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
    content: 'Publish',
    trigger: '.o_menu_systray .o_menu_systray_item:contains("Unpublished")',
}, {
    content: 'Wait for Publish',
    trigger: '.o_menu_systray .o_menu_systray_item:contains("Published"):not([data-processing])',
    run: () => {}, // This is a check.
}, {
    content: 'Unpublish',
    trigger: '.o_menu_systray .o_menu_systray_item:contains("Published")',
}, {
    content: 'Wait for Unpublish',
    trigger: '.o_menu_systray .o_menu_systray_item:contains("Unpublished"):not([data-processing])',
    run: () => {}, // This is a check.
}];

const cannotPublish = () => [{
    content: 'Check has no Publish/Unpublish',
    trigger: '.o_menu_systray:not(:has(.o_menu_systray_item:contains("ublished")))',
    run: () => {}, // This is a check.
}];

const canToggleMobilePreview = () => [{
    content: 'Enable mobile preview',
    trigger: '.o_menu_systray .o_menu_systray_item.o_mobile_preview:not(.o_mobile_preview_active) span',
}, {
    content: 'Disable mobile preview',
    trigger: '.o_menu_systray .o_menu_systray_item.o_mobile_preview.o_mobile_preview_active span',
}];

const cannotToggleMobilePreview = () => [{
    content: 'Enable mobile preview',
    trigger: '.o_menu_systray:not(:has(.o_menu_systray_item.o_mobile_preview))',
    run: () => {}, // This is a check.
}];

// For non-website users, switching across website only works if the domains are
// specified. Within the scope of test tours, this cannot be achieved.
const canSwitchWebsiteNoCheck = () => [{
    content: 'Open website switcher',
    trigger: '.o_menu_systray .o_menu_systray_item.o_website_switcher_container .dropdown-toggle:contains("My Website"):not(:contains("My Website 2"))',
}, {
    content: 'Switch to other website',
    trigger: '.o_menu_systray .o_menu_systray_item.o_website_switcher_container .dropdown-item:contains("Other")',
    run: () => {}, // This is a check.
}];


const canSwitchWebsite = () => [{
    content: 'Open website switcher',
    trigger: '.o_menu_systray .o_menu_systray_item.o_website_switcher_container .dropdown-toggle:contains("My Website"):not(:contains("My Website 2"))',
}, {
    content: 'Switch to other website',
    trigger: '.o_menu_systray .o_menu_systray_item.o_website_switcher_container .dropdown-item:contains("Other")',
}, {
    content: 'Wait for other website',
    trigger: 'iframe body:contains("Test Model") div:contains("Other")',
    run: () => {}, // This is a check.
}];

const canAddNewContent = () => [{
    content: 'Open +New content',
    trigger: '.o_menu_systray .o_menu_systray_item.o_new_content_container',
}, {
    content: 'Close +New content',
    trigger: '#o_new_content_menu_choices',
}];

const cannotAddNewContent = () => [{
    content: 'No +New content',
    trigger: '.o_menu_systray:not(:has(.o_menu_systray_item.o_new_content_container))',
    run: () => {}, // This is a check.
}];

const canEditInBackEnd = () => [{
    content: 'Edit in backend',
    trigger: '.o_menu_systray .o_website_edit_in_backend a',
}, {
    content: 'Check that the form is editable',
    trigger: '.o_form_view_container .o_form_editable',
    run: () => {}, // This is a check.
}, {
    content: 'Return to website',
    trigger: '.o-form-buttonbox .fa-globe',
}];

const canViewInBackEnd = () => [{
    content: 'Go to backend',
    trigger: '.o_menu_systray .o_website_edit_in_backend a',
}, {
    content: 'Check that the form is read-only',
    trigger: '.o_form_view_container .o_form_readonly',
    run: () => {}, // This is a check.
}, {
    content: 'Return to website',
    trigger: '.o-form-buttonbox .fa-globe',
}];

const canEdit = () => [
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: 'Click on name',
        trigger: 'iframe span[data-oe-expression="test_model.name"][contenteditable="true"]',
    }, {
        content: 'Change name',
        trigger: 'iframe span[data-oe-expression="test_model.name"][contenteditable="true"]',
        run: 'text Better name',
    }, {
        content: 'Check that field becomes dirty',
        trigger: 'iframe span[data-oe-expression="test_model.name"].o_dirty',
        run: () => {}, // This is a check.
    },
    ...wTourUtils.clickOnSave(),
    {
        content: 'Check whether name is saved',
        trigger: 'iframe span[data-oe-expression="test_model.name"]:contains("Better name")',
        run: () => {}, // This is a check.
    },
];

const cannotEdit = () => [{
    content: 'Check Edit is not available',
    trigger: '.o_menu_systray:not(:has(.o_edit_website_container))',
    run: () => {}, // This is a check.
}];

const canEditButCannotChange = () => [
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: 'Cannot change name',
        trigger: 'iframe main:not(:has([data-oe-expression])):contains("Test Model")',
        run: () => {}, // This is a check.
    },
];

const register = (title, steps) => {
    wTourUtils.registerWebsitePreviewTour(title, {
        url: '/test_model/1',
        test: true,
    }, steps);
};

register('test_systray_admin', () => [
    ...canPublish(),
    ...canToggleMobilePreview(),
    ...canSwitchWebsite(),
    ...canAddNewContent(),
    ...canEditInBackEnd(),
    ...canEdit(),
]);

register('test_systray_reditor_tester', () => [
    ...canPublish(),
    ...canToggleMobilePreview(),
    ...canSwitchWebsite(),
    ...canAddNewContent(),
    ...canEditInBackEnd(),
    ...canEdit(),
]);

register('test_systray_reditor_not_tester', () => [
    ...cannotPublish(),
    ...canToggleMobilePreview(),
    ...canSwitchWebsite(),
    ...canAddNewContent(),
    ...canViewInBackEnd(),
    ...canEditButCannotChange(),
]);

register('test_systray_not_reditor_tester', () => [
    ...canPublish(),
    ...cannotToggleMobilePreview(),
    ...canSwitchWebsiteNoCheck(),
    ...cannotAddNewContent(),
    ...canEditInBackEnd(),
    ...cannotEdit(),
]);

register('test_systray_not_reditor_not_tester', () => [
    ...cannotPublish(),
    ...cannotToggleMobilePreview(),
    ...canSwitchWebsiteNoCheck(),
    ...cannotAddNewContent(),
    ...canViewInBackEnd(),
    ...cannotEdit(),
]);
