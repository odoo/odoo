import { registry } from "@web/core/registry";
import { LinkTrackerDialog } from "../components/dialog/link_tracker_dialog";
import { browser } from "@web/core/browser/browser";

registry.category("website_custom_menus").add("website_links.menu_link_tracker", {
    // openWidget: (services) => services.website.goToWebsite({ path: `/r?u=${encodeURIComponent(services.website.contentWindow.location.href)}` }),
    Component: LinkTrackerDialog,
    isDisplayed: (env) => env.services.website.currentWebsite && env.services.website.contentWindow,
    getProps: async ({ orm, website }) => {
        const model = "link.tracker";
        return {
            resModel: model,
            onRecordSaved: async (record) => {
                const params = {
                    url: record.data.url,
                    campaign_id: record.data.campaign_id[0],
                    medium_id: record.data.medium_id[0],
                    source_id: record.data.source_id[0],
                    label: record.data.label,
                };
                const isRecordCreated = await orm.call(model, "search_or_create", [params]);

                if (isRecordCreated) {
                    browser.navigator.clipboard.writeText(record.data.url);
                    website.websiteRootInstance.options.services.notification.add(
                        "Your tracked link is now created & copied !",
                        { type: "success" }
                    );
                }
            },
        };
    },
});
