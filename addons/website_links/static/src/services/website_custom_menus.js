import { registry } from "@web/core/registry";
import { LinkTrackerDialog } from "../components/dialog/link_tracker_dialog";
import { browser } from "@web/core/browser/browser";

registry.category("website_custom_menus").add("website_links.menu_link_tracker", {
    Component: LinkTrackerDialog,
    isDisplayed: (env) => env.services.website.currentWebsite && env.services.website.contentWindow,
    getProps: async ({ orm, website }) => {
        const model = "link.tracker";
        return {
            resModel: model,
            onRecordSaved: async (record) => {
                const { url, campaign_id, medium_id, source_id, label } = record.data;
                const params = {
                    url,
                    campaign_id: campaign_id[0],
                    medium_id: medium_id[0],
                    source_id: source_id[0],
                    label,
                };
                const isRecordCreated = await orm.call(model, "search_or_create", [params]);

                if (isRecordCreated) {
                    await browser.navigator.clipboard.writeText(url);
                    website.websiteRootInstance.options.services.notification.add(
                        "Your tracked link is now created & copied!",
                        { type: "success" }
                    );
                }
            },
        };
    },
});
