/** @odoo-module native */
import { Component, useState, xml } from "@odoo/owl";
import { CheckBox } from "@web/components/checkbox";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { useBus, useService } from "@web/core/utils/hooks";
import { OptimizeSEODialog } from "@website/components/dialog/seo";
import { checkAndNotifySEO } from "@website/js/utils";

const websiteSystrayRegistry = registry.category("website_systray");

const log = makeLogger("website.systray.publish");

export class PublishSystrayItem extends Component {
    static template = xml`
        <div t-on-click="this.publishContent" class="o_menu_systray_item o_website_publish_container d-flex ms-auto" t-att-data-processing="this.state.processing and 1">
            <a href="#" class="d-flex align-items-center mx-1 px-2 px-md-0" data-hotkey="p">
                <span class="o_nav_entry d-none d-md-block mx-0 pe-1" t-out="this.label"/>
                <CheckBox value="this.state.published" className="'form-switch d-flex justify-content-center m-0 pe-none'"/>
            </a>
        </div>`;
    static components = {
        CheckBox,
    };
    static props = {};

    setup() {
        useLifecycleLog(log);
        this.website = useService("website");
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");

        this.state = useState({
            published: this.website.currentWebsite.metadata.isPublished,
            processing: false,
        });

        useBus(
            websiteSystrayRegistry,
            "CONTENT-UPDATED",
            () =>
                (this.state.published =
                    this.website.currentWebsite.metadata.isPublished),
        );
    }

    get label() {
        return this.state.published ? _t("Published") : _t("Unpublished");
    }

    async publishContent() {
        if (this.state.processing) {
            log.logic("publishContent skip: already processing");
            return;
        }
        this.state.processing = true;
        this.state.published = !this.state.published;
        const {
            metadata: { mainObject },
        } = this.website.currentWebsite;
        const endPublish = log.perf("website_publish_button", () => ({
            model: mainObject.model,
            id: mainObject.id,
        }));
        return this.orm
            .call(mainObject.model, "website_publish_button", [[mainObject.id]])
            .then(
                async (published) => {
                    endPublish({ published });
                    this.state.published = published;
                    if (
                        published &&
                        this.website.currentWebsite.metadata.canOptimizeSeo
                    ) {
                        const endSeo = log.perf("get_seo_data after publish");
                        const seo_data = await rpc("/website/get_seo_data", {
                            res_id: mainObject.id,
                            res_model: mainObject.model,
                        });
                        endSeo();
                        checkAndNotifySEO(seo_data, OptimizeSEODialog, {
                            notification: this.notificationService,
                            dialog: this.dialogService,
                        });
                    }
                    this.state.processing = false;
                    return published;
                },
                (err) => {
                    log.logic("publishContent failed: revert toggle", () => ({
                        message: err?.message,
                    }));
                    this.state.published = !this.state.published;
                    this.state.processing = false;
                    throw err;
                },
            );
    }
}
