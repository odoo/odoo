import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { useService, useBus } from "@web/core/utils/hooks";
import { Component, xml, useState } from "@odoo/owl";
import { OptimizeSEODialog } from "@website/components/dialog/seo";
import { checkAndNotifySEO } from "@website/js/utils";

const websiteSystrayRegistry = registry.category("website_systray");

export class PublishSystrayItem extends Component {
    static template = xml`
        <div t-on-click="publishContent" class="o_menu_systray_item o_website_publish_container d-flex ms-auto" t-att-data-processing="state.processing and 1">
            <a href="#" class="d-flex align-items-center mx-1 px-2 px-md-0" data-hotkey="p">
                <span class="o_nav_entry d-none d-md-block mx-0 pe-1" t-esc="this.label"/>
                <CheckBox value="state.published" className="'form-switch d-flex justify-content-center m-0 pe-none'"/>
            </a>
        </div>`;
    static components = {
        CheckBox,
    };
    static props = {};

    setup() {
        this.website = useService("website");
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");

        this.state = useState({
            published: this.website.currentWebsite.metadata.isPublished,
            processing: false,
        });

        // TODO: website service should share a reactive
        useBus(
            websiteSystrayRegistry,
            "CONTENT-UPDATED",
            () => (this.state.published = this.website.currentWebsite.metadata.isPublished)
        );
    }

    get label() {
        return this.state.published ? _t("Published") : _t("Unpublished");
    }

    async publishContent() {
        if (this.state.processing) {
            return;
        }
        this.state.processing = true;
        this.state.published = !this.state.published;
        const {
            metadata: { mainObject },
        } = this.website.currentWebsite;
        return this.orm.call(mainObject.model, "website_publish_button", [[mainObject.id]]).then(
            async (published) => {
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
                this.state.processing = false;
                return published;
            },
            (err) => {
                this.state.published = !this.state.published;
                this.state.processing = false;
                throw err;
            }
        );
    }
}
