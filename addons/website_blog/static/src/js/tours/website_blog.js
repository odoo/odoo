/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import {
    clickOnSave,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

import { markup } from "@odoo/owl";

registerWebsitePreviewTour("blog", {
    url: "/",
}, () => [{
    trigger: "body:not(:has(#o_new_content_menu_choices)) .o_new_content_container > a",
    content: _t("Click here to add new content to your website."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: 'a[data-module-xml-id="base.module_website_blog"]',
    content: _t("Select this menu item to create a new blog post."),
    tooltipPosition: "bottom",
    run: "click",
}, {
    trigger: 'div[name="name"] input',
    content: _t("Enter your post's title"),
    tooltipPosition: "bottom",
    run: "edit Test",
},
{
    isActive: ["auto"],
    trigger: 'div.o_field_widget[name="blog_id"]',
},
{
    isActive: ["auto"],
    trigger: "button.o_form_button_save",
    content: _t("Select the blog you want to add the post to."),
    // Without demo data (and probably in most user cases) there is only
    // one blog so this step would not be needed and would block the tour.
    // We keep the step with "auto: true", so that the main python test
    // still works but never display this to the user anymore. We suppose
    // the user does not need guidance once that modal is opened. Note: if
    // you run the tour via your console without demo data, the tour will
    // thus fail as this will be considered.
    run: "click",
},
{
    isActive: ["auto"],
    trigger: "#oe_snippets.o_loaded",
    timeout: 15000,
},
{
    trigger: ":iframe h1[data-oe-expression=\"blog_post.name\"]",
    content: _t("Edit your title, the subtitle is optional."),
    tooltipPosition: "top",
    run: "editor Test",
},
{
    isActive: ["auto"],
    trigger: `:iframe #wrap h1[data-oe-expression="blog_post.name"]:not(:contains(''))`,
},
{
    trigger: "we-button[data-background]:eq(0)",
    content: markup(_t("Set a blog post <b>cover</b>.")),
    tooltipPosition: "top",
    run: "click",
}, {
    trigger: ".o_select_media_dialog .o_we_search",
    content: _t("Search for an image. (eg: type \"business\")"),
    tooltipPosition: "top",
},
{
    trigger: ".o_select_media_dialog .o_existing_attachment_cell:first img",
    content: _t("Choose an image from the library."),
    tooltipPosition: "top",
    run: "click",
}, {
    trigger: ":iframe #o_wblog_post_content p",
    content: markup(_t("<b>Write your story here.</b> Use the top toolbar to style your text: add an image or table, set bold or italic, etc. Drag and drop building blocks for more graphical blogs.")),
    tooltipPosition: "top",
    run: "editor Blog content",
},
...clickOnSave(),
{
    trigger: ".o_menu_systray_item.o_mobile_preview > a",
    content: markup(_t("Use this icon to preview your blog post on <b>mobile devices</b>.")),
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["auto"],
    trigger: ".o_website_preview.o_is_mobile",
},
{
    trigger: ".o_menu_systray_item.o_mobile_preview > a",
    content: _t("Once you have reviewed the content on mobile, you can switch back to the normal view by clicking here again"),
    tooltipPosition: "right",
    run: "click",
},
{
    isActive: ["auto"],
    trigger: ":iframe body:not(.editor_enable)",
},
{
    trigger: '.o_menu_systray_item a:contains("Unpublished")',
    tooltipPosition: "bottom",
    content: markup(_t("<b>Publish your blog post</b> to make it visible to your visitors.")),
    run: "click",
}, {
    isActive: ["auto"],
    trigger: '.o_menu_systray_item a:contains("Published")',
}
]);
