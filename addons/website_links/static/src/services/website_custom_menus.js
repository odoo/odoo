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
            onRecordSave: async function (record) {
                if (!record._checkValidity({ displayNotification: true })) {
                    return false;
                }
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
                    // Note: The following code is used to update the resId and resIds of the record's config.
                    // Replicate same logic done in _save method of Record class
                    // usually it should be done in _save method but as we have custom save mechanism
                    // we have to explicitly update the resId and resIds otherwise record will not have right
                    // resId and resIds after save and it will cause issues when we try to expand the record
                    const resId = records[0].id;
                    const resIds = record.resIds.concat([resId]);
                    record.model._updateConfig(
                        record.config,
                        { resId: resId, resIds },
                        { reload: false }
                    );

                    const trackUrl = records[0].short_url;
                    await browser.navigator.clipboard.writeText(trackUrl);
                    const message = _t(
                        "Tracked link copied to clipboard%(br)s%(open_span)sLink: %(tracked_link)s%(close_span)s",
                        {
                            open_span: markup`<span class="o_line_clamp o_line_clamp_1">`,
                            tracked_link: trackUrl.replace(session["web.base.url"], ""),
                            br: markup`<br>`,
                            close_span: markup`</span>`,
                        }
                    );
                    const closeNotification = notification.add(message, {
                        type: "success",
                        buttons: [
                            {
                                name: _t("Manage"),
                                primary: true,
                                onClick: () => {
                                    closeNotification();
                                    browser.location.href =
                                        "/odoo/action-website_links.action_link_tracker_tree";
                                },
                            },
                        ],
                    });
                }
                return records;
            },
        };
    },
});
