import { _t } from "@web/core/l10n/translation";
import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { useService, useBus } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { OptimizeSEODialog } from "@website/components/dialog/seo";
import { RelativePublishTime } from "./relative_publish_time";

const websiteSystrayRegistry = registry.category("website_systray");

/**
 * Checks SEO data and notifies if either the page title or description is not
 * set.
 *
 * @param {Object} seo_data - The SEO data to check.
 * @param {Component} OptimizeSEODialog - Dialog to be displayed
 * @param {Object} services - Services object which will be used to display
 * notifications and dialog.
 */
export function checkAndNotifySEO(seo_data, OptimizeSEODialog, services) {
    if (seo_data) {
        let message;
        if (!seo_data.website_meta_title) {
            message = _t("Page title not set.");
        } else if (!seo_data.website_meta_description) {
            message = _t("Page description not set.");
        }
        if (message) {
            const closeNotification = services.notification.add(message, {
                type: "warning",
                sticky: false,
                buttons: [
                    {
                        name: _t("Optimize SEO"),
                        onClick: () => {
                            services.dialog.add(OptimizeSEODialog);
                            closeNotification();
                        },
                    },
                ],
            });
        }
    }
}

export class PublishSystrayItem extends Component {
    static template = "website.PublishSystrayItem";
    static components = {
        CheckBox,
        RelativePublishTime,
    };
    static props = {};

    setup() {
        this.website = useService("website");
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");
        this.actionService = useService("action");
        this.websiteCustomMenus = useService("website_custom_menus");

        this.state = useState({
            published: false,
            scheduled: false,
            publishOn: false,
            formattedPublishAt: false,
            processing: false,
        });
        this.updateState();

        // TODO: website service should share a reactive
        useBus(websiteSystrayRegistry, "CONTENT-UPDATED", this.updateState);
    }

    get label() {
        return this.state.published ? _t("Published") : _t("Unpublished");
    }

    onContainerClick() {
        if (this.state.scheduled) {
            return;
        }
        this.publishContent();
    }

    async publishContent() {
        if (this.state.processing) {
            return;
        }
        this.state.published = !this.state.published;
        const {
            metadata: { mainObject },
        } = this.website.currentWebsite;
        this.state.processing = true;
        try {
            const published = await this.orm.call(mainObject.model, "website_publish_button", [
                [mainObject.id],
            ]);
            this.state.published = published;
            if (published && this.website.currentWebsite.metadata.canOptimizeSeo) {
                const seo_data = await rpc("/website/get_seo_data", {
                    res_id: mainObject.id,
                    res_model: mainObject.model,
                });
                checkAndNotifySEO(seo_data, OptimizeSEODialog, {
                    notification: this.notificationService,
                    dialog: this.dialogService,
                });
            }
            if (this.state.published) {
                this.state.scheduled = false;
                this.state.publishOn = false;
                this.state.formattedPublishAt = false;
            }
            return published;
        } catch (err) {
            this.state.published = !this.state.published;
            throw err;
        } finally {
            this.state.processing = false;
        }
    }

    updateState = () => {
        const metadata = this.website.currentWebsite?.metadata || {};
        this.state.published = !!metadata.isPublished;
        const publishOn = metadata.publishOn;
        this.state.scheduled = !!publishOn;
        this.state.publishOn = publishOn
            ? deserializeDateTime(publishOn, {
                  tz: this.website.currentWebsite.metadata?.mainObject?.tz,
              })
            : false;
        this.state.formattedPublishAt = formatDateTime(this.state.publishOn) || false;
    };

    triggerPublish() {
        this.state.published = true;
        this.state.scheduled = false;
        this.state.publishOn = false;
        this.state.formattedPublishAt = false;
    }

    editInBackend() {
        const {
            metadata: { mainObject },
        } = this.website.currentWebsite;
        if (mainObject.model === "website.page") {
            this.websiteCustomMenus.open({
                xmlid: "website.menu_page_properties",
            });
        } else {
            this.actionService.doAction({
                res_model: mainObject.model,
                res_id: mainObject.id,
                views: [[false, "form"]],
                type: "ir.actions.act_window",
                view_mode: "form",
            });
        }
    }
}
