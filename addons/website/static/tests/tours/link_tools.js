/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';
import { boundariesIn, setSelection } from '@web_editor/js/editor/odoo-editor/src/utils/utils';

const clickOnImgStep = {
    content: "Click somewhere else to save.",
    trigger: 'iframe #wrap .s_text_image img',
};

wTourUtils.registerWebsitePreviewTour('link_tools', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    // 1. Create a new link from scratch.
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    {
        content: "Replace first paragraph, to insert a new link",
        trigger: 'iframe #wrap .s_text_image p',
        run: 'text Go to odoo: '
    },
    {
        content: "Open link tools",
        trigger: "#toolbar:not(.oe-floating) #create-link",
    },
    {
        content: "Type the link URL odoo.com",
        trigger: '#toolbar:not(.oe-floating) #o_link_dialog_url_input',
        run: 'text odoo.com'
    },
    clickOnImgStep,
    // 2. Edit the link with the link tools.
    {
        content: "Click on the newly created link",
        trigger: 'iframe .s_text_image a[href="http://odoo.com"]:contains("odoo.com")',
    },
    {
        content: "Label value should contain odoo.com",
        trigger: '#o_link_dialog_label_input',
        run: () => {
            if ($('#o_link_dialog_label_input').val() !== 'odoo.com') {
                throw new Error('Label value should contain odoo.com');
            }
        },
    },
    {
        content: "Change content (editing the label input) to odoo website_2",
        trigger: '#o_link_dialog_label_input',
        run: 'text odoo website_2',
    },
    {
        content: "Click again on the link",
        trigger: 'iframe .s_text_image a[href="http://odoo.com"]:contains("odoo website_2")',
    },
    {
        content: "Change content (editing the DOM) to odoo website",
        trigger: 'iframe .s_text_image a[href="http://odoo.com"]:contains("odoo website_2")',
        run: 'text odoo website',
    },
    clickOnImgStep,
    {
        content: "Click again on the link",
        trigger: 'iframe .s_text_image a[href="http://odoo.com"]:contains("odoo website")',
    },
    {
        content: "Label value should contain odoo website",
        trigger: '#o_link_dialog_label_input',
        run: () => {
            if ($('#o_link_dialog_label_input').val() !== 'odoo website') {
                throw new Error('Label value should contain odoo website');
            }
        },
    },
    {
        content: "Link tools, should be open, change the url",
        trigger: '#o_link_dialog_url_input',
        run: 'text_blur odoo.be'
    },

    ...wTourUtils.clickOnSave(),
    // 3. Edit a link after saving the page.
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    clickOnImgStep,
    {
        content: "The new link content should be odoo website and url odoo.be",
        trigger: 'iframe .s_text_image a[href="http://odoo.be"]:contains("odoo website")',
    },
    {
        content: "The new link content should be odoo website and url odoo.be",
        trigger: '#toolbar:not(.oe-floating) .dropdown:has([name="link_style_color"]) > button',
    },
    {
        content: "Click on the secondary style button.",
        trigger: '#toolbar:not(.oe-floating) we-button[data-value="secondary"]',
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "The link should have the secondary button style.",
        trigger: 'iframe .s_text_image a.btn.btn-secondary[href="http://odoo.be"]:contains("odoo website")',
        run: () => {}, // It's a check.
    },
    // 4. Add link on image.
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.dragNDrop({
        id: 's_three_columns',
        name: 'Columns',
    }),
    {
        content: "Click on the first image.",
        trigger: 'iframe .s_three_columns .row > :nth-child(1) img',
    },
    {
        content: "Activate link.",
        trigger: '.o_we_customize_panel we-row:contains("Media") we-button.fa-link',
    },
    {
        content: "Set URL.",
        trigger: '.o_we_customize_panel we-input:contains("Your URL") input',
        run: 'text odoo.com',
    },
    {
        content: "Deselect image.",
        trigger: 'iframe .s_three_columns .row > :nth-child(2) img',
    },
    {
        content: "Re-select image.",
        trigger: 'iframe .s_three_columns .row > :nth-child(1) img',
    },
    {
        content: "Check that the second image is not within a link.",
        trigger: 'iframe .s_three_columns .row > :nth-child(2) div > img',
        run: () => {}, // It's a check.
    },
    {
        content: "Check that link tools appear.",
        trigger: 'iframe .popover div a:contains("http://odoo.com")',
        run: () => {}, // It's a check.
    },
    // 5. Remove link from image.
    {
        content: "Remove link.",
        trigger: 'iframe .popover:contains("http://odoo.com") a .fa-chain-broken',
    },
    {
        content: "Check that image is not within a link anymore.",
        trigger: 'iframe .s_three_columns .row > :nth-child(1) div > img',
        run: () => {}, // It's a check.
    },
    ...wTourUtils.clickOnSave(),
    // 6. Create new a link from a URL-like text.
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Replace first paragraph, write a URL",
        trigger: 'iframe #wrap .s_text_image p',
        run: 'text odoo.com'
    },
    {
        content: "Select text",
        trigger: 'iframe #wrap .s_text_image p:contains(odoo.com)',
        run() {
            setSelection(...boundariesIn(this.$anchor[0]), false);
        }
    },
    {
        content: "Open link tools",
        trigger: "#toolbar #create-link",
    },
    clickOnImgStep,
    {
        // URL transformation into link should persist, without the need for
        // input at input[name=url]
        content: "Check that link was created",
        trigger: "iframe .s_text_image p a[href='http://odoo.com']:contains('odoo.com')",
        run: () => null,
    },
    {
        content: "Click on link to open the link tools",
        trigger: "iframe .s_text_image p a",
    },
    {
        // Click on the LinkTools to make the popover close.
        trigger: "#o_link_dialog_url_input",
    },
    {
        // Wait for popover to close.
        trigger: 'iframe html:not(:has(.popover))',
        run: () => null,
    },
    // 7. Check that http links are not coerced to https and vice-versa.
    {
        content: "Change URL to https",
        trigger: "#o_link_dialog_url_input",
        run: 'text https://odoo.com',
    },
    {
        content: "Check that link was updated",
        trigger: "iframe .s_text_image p a[href='https://odoo.com']:contains('odoo.com')",
        run: () => null,
    },
    {
        content: "Change it back http",
        trigger: "#o_link_dialog_url_input",
        run: 'text http://odoo.com',
    },
    {
        content: "Check that link was updated",
        trigger: "iframe .s_text_image p a[href='http://odoo.com']:contains('odoo.com')",
        run: () => null,
    },
    // 8. Test conversion between http and mailto links.
    {
        content: "Change URL into an email address",
        trigger: "#o_link_dialog_url_input",
        run: "text callme@maybe.com",
    },
    {
        content: "Check that link was updated and link content is synced with URL",
        trigger: "iframe .s_text_image p a[href='mailto:callme@maybe.com']:contains('callme@maybe.com')",
        run: () => null,
    },
    {
        content: "Change URL back into a http one",
        trigger: "#o_link_dialog_url_input",
        run: "text_blur callmemaybe.com",
    },
    {
        content: "Check that link was updated and link content is synced with URL",
        trigger: "iframe .s_text_image p a[href='http://callmemaybe.com']:contains('callmemaybe.com')",
        run: () => null,
    },
    // 9.Test that UI stays up-to-date.
    {
        content: "Click on link to open popover",
        trigger: "iframe .s_text_image p a[href='http://callmemaybe.com']:contains('callmemaybe.com')",
    },
    {
        content: "LinkTools should be opened",
        trigger: "#toolbar:not(.oe-floating) #o_link_dialog_url_input",
        run: () => null,
    },
    {
        content: "Popover should be shown",
        trigger: "iframe .o_edit_menu_popover .o_we_url_link:contains('http://callmemaybe.com')",
        run: () => null,
    },
    {
        content: "Edit link label",
        trigger: "iframe .s_text_image p a",
        run(actions) {
            actions.text("callmemaybe.com/shops");
            // Make sure to trigger an history step.
            // Trick the editor into keyboardType === 'PHYSICAL' and delete the
            // last character "s" and end with "callmemaybe.com/shop"
            const link = this.$anchor[0];
            link.dispatchEvent(new KeyboardEvent("keydown", { key: "Backspace", bubbles: true }));
            // Trigger editor's '_onInput' handler.
            link.dispatchEvent(new InputEvent('input', {inputType: 'insertText', bubbles: true}));
        },
    },
    {
        content: "Check that links's href was updated",
        trigger: "iframe .s_text_image p a[href='http://callmemaybe.com/shop']:contains('callmemaybe.com/shop')",
        run: () => null,
    },
    {
        content: "Check popover content is up-to-date",
        trigger: "iframe .popover div a:contains('http://callmemaybe.com/shop')",
        run: () => null,
    },
    {
        content: "Check Link tools URL input content is up-to-date",
        trigger: "#o_link_dialog_url_input",
        run() {
            if (this.$anchor[0].value !== 'callmemaybe.com/shop') {
                throw new Error("Tour step failed");
            }
        }
    },
     // 10.Pick a URL with auto-complete
    {
        content: "Enter partial URL",
        trigger: "#o_link_dialog_url_input",
        run: 'text /contact'
    },
    {
        content: "Pick '/contactus",
        trigger: "ul.ui-autocomplete li div:contains('/contactus (Contact Us)')",
    },
    {
        content: "Check that links's href and label were updated",
        trigger: "iframe .s_text_image p a[href='/contactus']:contains('/contactus')",
        run: () => null,
    },
    // 11. Add a link leading to a 404 page
    {
        content: "Enter a non-existent URL",
        trigger: "#o_link_dialog_url_input",
        run: "text /this-address-does-not-exist",
    },
    {
        content: "Check that the link's href was updated and click on it",
        trigger: "iframe .s_text_image p a[href='/this-address-does-not-exist']",
    },
    {
        content: "Check popover content is up-to-date",
        trigger: "iframe .popover div a:contains('/this-address-does-not-exist')",
        isCheck: true,
    },
    ...wTourUtils.clickOnSave(),
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    // 12. Add mega menu with Cards template and edit URL on text-selected card.
    wTourUtils.clickOnElement("menu link", "iframe header .nav-item a"),
    wTourUtils.clickOnElement("'Edit menu' icon", "iframe .o_edit_menu_popover .fa-sitemap"),
    {
        content: "Click on 'Add Mega Menu Item' link",
        extra_trigger: '.o_website_dialog:visible',
        trigger: ".modal-body a:contains('Add Mega Menu Item')",
    },
    {
        content: "Enter mega menu name",
        trigger: ".modal-body input",
        run: "text Mega",
    },
    wTourUtils.clickOnElement("OK button", ".btn-primary"),
    {
        content: "Drag Mega at the top",
        trigger: '.oe_menu_editor li:contains("Mega") .fa-bars',
        run: "drag_and_drop_native .oe_menu_editor li:contains('Home') .fa-bars",
    },
    {
        content: "Wait for drop",
        trigger: '.oe_menu_editor:first-child:contains("Mega")',
        run: () => {}, // This is a check.
    },
    wTourUtils.clickOnElement("Save button", ".btn-primary:contains('Save')"),
    wTourUtils.clickOnElement("mega menu", "iframe header .o_mega_menu_toggle"),
    wTourUtils.changeOption("MegaMenuLayout", "we-toggler"),
    wTourUtils.changeOption("MegaMenuLayout", '[data-select-label="Cards"]'),
    wTourUtils.clickOnElement("card's text", "iframe header .s_mega_menu_cards p"),
    {
        content: "Enter an URL",
        trigger: "#o_link_dialog_url_input",
        run: "text https://www.odoo.com",
    },
    {
        content: "Check nothing is lost",
        trigger: "iframe header .s_mega_menu_cards a[href='https://www.odoo.com']:has(img):has(h4):has(p)",
        run: () => {}, // This is a check.
    },
    // 11. Check that ZWS is not added in the link label input.
    clickOnImgStep,
    {
        content: "Click on contact us button",
        trigger: "iframe a.btn[href='/contactus']",
    },
    {
        content: "Verify that the link label input does not contain ZWS",
        trigger: "#o_link_dialog_label_input:propValue('Contact Us')",
        isCheck: true,
    },
    ...wTourUtils.clickOnSave(),
]);
