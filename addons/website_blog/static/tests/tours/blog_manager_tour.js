import wTourUtils from "@website/js/tours/tour_utils";
import { _t } from "@web/core/l10n/translation";

/**
 * Makes sure that blog are only managable by Blog Manager Group.
 * it tests that whether a user with blog manager rights are able to create or edit
 * website blog or not.
 */
wTourUtils.registerWebsitePreviewTour("blog_manager", {
    test: true,
    url: "/blog",
}, () => [{
        trigger: "body:not(:has(#o_new_content_menu_choices)) .o_new_content_container > a",
        content: _t("Click here to add new content to your website."),
        consumeVisibleOnly: true,
        position: "bottom",
        run: "click",
    }, {
        trigger: "a[data-module-xml-id='base.module_website_blog']",
        content: _t("Select this menu item to create a new blog post."),
        position: "bottom",
        run: "click",
    }, {
        trigger: "div[name='name'] input",
        content: _t("Enter your post's title"),
        position: "bottom",
        run: "edit Manager Blog",
    }, {
        trigger: "button.o_form_button_save",
        extra_trigger: "div.o_field_widget[name='blog_id']",
        content: _t("Select the blog you want to add the post to."),
        // Without demo data (and probably in most user cases) there is only
        // one blog so this step would not be needed and would block the tour.
        // We keep the step with "auto: true", so that the main python test
        // still works but never display this to the user anymore. We suppose
        // the user does not need guidance once that modal is opened. Note: if
        // you run the tour via your console without demo data, the tour will
        // thus fail as this will be considered.
        auto: true,
        run: "click",
    },
    ...wTourUtils.clickOnSave(),
    {
        trigger: ":iframe article[name=blog_post] a:contains('Manager Blog')",
        content: _t("Go to the 'Manager Blog' blog"),
        run: "click",
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        trigger: ":iframe h1[data-oe-expression='blog_post.name']",
        extra_trigger: "#oe_snippets.o_loaded",
        content: _t("Edit your Blog title"),
        position: "top",
        run: "editor Manager Blog Test Title",
    },
    {
        trigger: ":iframe #o_wblog_post_content p",
        content: _t("Edit your Blog content."),
        position: "top",
        run: "editor Manager Blog Test Content",
    },
    ...wTourUtils.clickOnSave(),
]);

/**
 * Makes sure that blog are only managable by Blog Manager Group.
 * it tests that whether a non manager user are able to create or edit
 * website blog or not.
 */
wTourUtils.registerWebsitePreviewTour("blog_no_manager", {
    test: true,
    url: "/blog",
}, () => [{
        trigger: "body:not(:has(#o_new_content_menu_choices)) .o_new_content_container > a",
        content: _t("Click here to add new content to your website."),
        consumeVisibleOnly: true,
        position: "bottom",
        run: "click",
    }, {
        trigger: "#o_new_content_menu_choices:not(a:has([data-module-xml-id='base.module_website_blog']))",
        content: _t("Check if Blog Post Option is Present or Not."),
    }, {
        trigger: "#o_new_content_menu_choices",
        content: _t("Close New Content Menu"),
        run: "click",
    }, {
        trigger: ":iframe article[name=blog_post] a:contains('Manager Blog Test Title')",
        content: _t("Go to the 'Manager Blog Test Title' blog"),
        run: "click",
    },
    // from here this tour tries to delete the
    // post from the backend side.
    {
        trigger: ".o_website_edit_in_backend a",
        content: _t("Open Post Form in Backend"),
        run: "click",
    }, {
        trigger: ".o_action_manager button[data-tooltip='Actions']",
        content: _t("Click on gear Icon"),
        run: "click",
    }, {
        trigger: ".o_popover span i:not(.fa-trash-o)",
        content: _t("Check if delete action is available or not"),
    }
]);
