import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { LinkTrackerDialog } from "../components/dialog/link_tracker_dialog";
import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { session } from "@web/session";

registry.category("website_custom_menus").add("website_links.menu_link_tracker", {
    Component: LinkTrackerDialog,
    isDisplayed: (env) => env.services.website.currentWebsite && env.services.website.contentWindow,
    getProps: async ({ orm, website, notification }) => {
        const model = "link.tracker";
        return {
            resModel: model,
            onRecordSave: async (record) => {
                const changes = await record.getChanges();
                const records = await orm.call(
                    "link.tracker",
                    "search_or_create_and_read",
                    [[changes]],
                    {}
                );
                // 'document.hasFocus()' is used to check if the browser tab is focused.
                // This check is necessary because, during the tour, it fails and gives
                // the error: "Failed to execute 'writeText' on 'Clipboard': Document is not focused."
                if (records.length && document.hasFocus()) {
                    const trackUrl = records[0].short_url;
                    await browser.navigator.clipboard.writeText(trackUrl);
                    const message = _t(
                        "Tracked link copied to clipboard%(br)s%(open_span)sLink: %(track_link)s%(close_span)s",
                        {
                            open_span: markup`<span style=" display: -webkit-box; -webkit-line-clamp: 1;
                                -webkit-box-orient: vertical; overflow: hidden;">`,
                            track_link: trackUrl.replace(session["web.base.url"], ""),
                            br: markup`<br>`,
                            close_span: markup`</span>`,
                        }
                    );
                    notification.add(message, {
                        type: "success",
                    });
                }
                return records;
            },
        };
    },
});
