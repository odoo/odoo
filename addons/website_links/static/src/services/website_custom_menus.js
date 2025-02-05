import { registry } from "@web/core/registry";
import { LinkTrackerDialog } from "../components/dialog/link_tracker_dialog";

registry.category("website_custom_menus").add("website_links.menu_link_tracker", {
    Component: LinkTrackerDialog,
    isDisplayed: (env) => env.services.website.currentWebsite && env.services.website.contentWindow,
    getProps: async ({ orm, website }) => {
        debugger;
        const mainObject = website.currentWebsite.metadata.mainObject;
        const isPage = mainObject.model === "website.page";
        const model = "link.tracker";
        return {
            resModel: model,
            onRecordSaved: async (record) => {
             debugger;
            },
        };
    },
});
