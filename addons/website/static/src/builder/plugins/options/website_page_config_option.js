import { BaseOptionComponent } from "@html_builder/core/utils";

export class TopMenuVisibilityOption extends BaseOptionComponent {
    static template = "website.TopMenuVisibilityOption";
    static dependencies = ["websitePageConfigOptionPlugin"];
    static selector =
        "[data-main-object]:has(input.o_page_option_data[name='header_visible']) #wrapwrap > header";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;

    setup() {
        super.setup();
        this.doesPageOptionExist =
            this.dependencies.websitePageConfigOptionPlugin.doesPageOptionExist;
    }
}
