/** @odoo-module */

import wTourUtils from 'website.tour_utils';
import { boundariesIn, setSelection } from '@web_editor/js/editor/odoo-editor/src/utils/utils';

const clickOnImgStep = {
    content: "Click somewhere else to save.",
    trigger: 'iframe #wrap .s_text_image img',
};

wTourUtils.registerWebsitePreviewTour('link_tools', {
    test: true,
    url: '/',
    edition: true,
}, [
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
        trigger: "#toolbar #create-link",
    },
    {
        content: "Type the link URL odoo.com",
        trigger: '#o_link_dialog_url_input',
        run: 'text odoo.com'
    },
    clickOnImgStep,
    // Remove the link.
    {
        content: "Click on the newly created link",
        trigger: 'iframe #wrap .s_text_image a[href="http://odoo.com"]:contains("odoo.com")',
    },
    {
        content: "Remove the link.",
        trigger: 'iframe .popover:contains("http://odoo.com") a .fa-chain-broken',
    },
    {
        content: "Check that the link was removed",
        trigger: 'iframe #wrap .s_text_image p:contains("Go to odoo:"):not(:has(a))',
        run: () => {}, // It's a check.
    },
    // Recreate the link.
    {
        content: "Select first paragraph, to insert a new link",
        trigger: 'iframe #wrap .s_text_image p',
    },
    {
        content: "Open link tools",
        trigger: "#toolbar #create-link",
    },
    {
        content: "Type the link URL odoo.com",
        trigger: '#o_link_dialog_url_input',
        run: 'text odoo.com'
    },
    clickOnImgStep,
    // 2. Edit the link with the link tools.
    {
        content: "Click on the newly created link",
        trigger: 'iframe .s_text_image a[href="http://odoo.com"]:contains("odoo.com")',
    },
    {
        content: "Change content (editing the label input) to odoo website_2",
        trigger: '#o_link_dialog_label_input[value="odoo.com"]',
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
        content: "Check that the label input contains the new content",
        trigger: '#o_link_dialog_label_input[value="odoo website"]',
        run: () => null, // it's a check
    },
    {
        content: "Link tools, should be open, change the url",
        trigger: '#o_link_dialog_url_input',
        run: 'text_blur odoo.be'
    },

    ...wTourUtils.clickOnSave(),
    // 3. Edit a link after saving the page.
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "The new link content should be odoo website and url odoo.be",
        trigger: 'iframe .s_text_image a[href="http://odoo.be"]:contains("odoo website")',
    },
    {
        content: "The new link content should be odoo website and url odoo.be",
        trigger: '#toolbar .dropdown:has([name="link_style_color"]) > button',
    },
    {
        content: "Click on the secondary style button.",
        trigger: '#toolbar we-button[data-value="secondary"]',
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
    ...wTourUtils.clickOnSave(),
    {
        content: "Check that the first image was saved.",
        trigger: 'iframe .s_three_columns .row > :nth-child(1) div > a > img',
        run: () => {}, // It's a check.
    },
    {
        content: "Check that the second image was saved.",
        trigger: 'iframe .s_three_columns .row > :nth-child(2) div > img',
        run: () => {}, // It's a check.
    },
    // 5. Remove link from image.
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Reselect the first image.",
        trigger: 'iframe .s_three_columns .row > :nth-child(1) div > a > img',
    },
    {
        content: "Check that link tools appear.",
        trigger: 'iframe .popover div a:contains("http://odoo.com")',
        run: () => {}, // It's a check.
    },
    {
        content: "Remove link.",
        trigger: 'iframe .popover:contains("http://odoo.com") a .fa-chain-broken',
    },
    {
        content: "Check that image is not within a link anymore.",
        trigger: 'iframe .s_three_columns .row > :nth-child(1) div > img',
        run: () => {}, // It's a check.
    },
    // 6. Add mega menu with Cards template and edit URL on text-selected card.
    // TODO somehow, if this testing phase is added at the end of the tour
    // (like it was before the introduction of this comment), there is a race
    // condition (last check: 57 over 162 tries failed on "Check popover content
    // is up-to-date"). It might not be due entirely be due to the re-order only
    // but to be investigated (probably something that can be made more robust
    // in earlier versions too): when this tour passes 100% of the time, make
    // sure it is the case when re-ordering phases before removing this comment.
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
        run: "drag_move_and_drop [0,0]@.oe_menu_editor li:contains('Home') .fa-bars => .oe_menu_editor li",
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
    wTourUtils.clickOnElement("card's text", "iframe header .s_mega_menu_cards font"),
    {
        content: "Enter an URL",
        trigger: "#o_link_dialog_url_input",
        run: "text https://www.odoo.com",
    },
    {
        content: "Check nothing is lost",
        trigger: "iframe header .s_mega_menu_cards a[href='https://www.odoo.com']:has(img):has(h4):has(p font)",
        run: () => {}, // This is a check.
    },
    // 7. Create new a link from a URL-like text.
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
    // 8. Check that http links are not coerced to https and vice-versa.
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
    // 9. Test conversion between http and mailto links.
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
    },
    // 10. Test that UI stays up-to-date.
    // TODO this step which was added by https://github.com/odoo/odoo/commit/9fc283b514d420fdfd66123845d9ec3563572692
    // for no apparent reason (the X-original-commit of that one does not add
    // this step) is not required for the test to work (it passes more often
    // without this step than with it). It is a cause of race condition (last
    // check: 31 over 162 tries failed on this). It however makes sense: the
    // popover should indeed be shown and stay shown at this point. To be
    // reenabled once the related feature is robust.
    /*
    {
        content: "Popover should be shown",
        trigger: "iframe .o_edit_menu_popover .o_we_url_link:contains('http://callmemaybe.com')",
        run: () => null,
    },
    */
    {
        content: "Edit link label",
        trigger: "iframe .s_text_image p a",
        run(actions) {
            // Simulating text input.
            const link = this.$anchor[0];
            actions.text("callmemaybe.com/shops");
            // Trick the editor into keyboardType === 'PHYSICAL' and delete the
            // last character "s" and end with "callmemaybe.com/shop"
            link.dispatchEvent(new KeyboardEvent("keydown", { key: "Backspace", bubbles: true }));
            // Trigger editor's '_onInput' handler, which leads to a history step.
            link.dispatchEvent(new InputEvent('input', {inputType: 'insertText', bubbles: true}));
        },
    },
    {
        content: "Check that links's href was updated",
        trigger: "iframe .s_text_image p a[href='http://callmemaybe.com/shop']:contains('callmemaybe.com/shop')",
        run: () => null,
    },
    // TODO this step is disabled for now because it is a cause of race
    // condition (last check: 57 over 162 tries failed on this). The popover
    // seems to sometimes unexpectedly close. Probably why the "Popover should
    // be shown" step above had to be disabled as well.
    /*
    {
        content: "Check popover content is up-to-date",
        trigger: "iframe .popover div a:contains('http://callmemaybe.com/shop')",
        run: () => null,
    },
    */
    {
        content: "Check Link tools URL input content is up-to-date",
        trigger: "#o_link_dialog_url_input",
        run() {
            if (this.$anchor[0].value !== 'http://callmemaybe.com/shop') {
                throw new Error("Tour step failed") ;
            }
        }
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
