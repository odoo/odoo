import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { LinkTrackerDialog } from "../components/dialog/link_tracker_dialog";
import { _t } from "@web/core/l10n/translation";

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
                const records = await orm.call(model, "search_or_create_and_read", [params]);

                // 'document.hasFocus()' is used to check if the browser tab is focused.
                // This check is necessary because, during the tour, it fails and gives
                // the error: "Failed to execute 'writeText' on 'Clipboard': Document is not focused."
                if (records.length && document.hasFocus()) {
                    const trackUrl = records[0].short_url;
                    await browser.navigator.clipboard.writeText(trackUrl);
                    website.websiteRootInstance.options.services.notification.add(
                        _t("Your tracked link is now created & copied!"),
                        { type: "success" }
                    );
                }
            },
        };
    },
});
