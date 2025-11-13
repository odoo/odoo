import { Component, useState } from "@odoo/owl";
import { useBus, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

const websiteSystrayRegistry = registry.category("website_systray");

export class EditWebsiteSystrayItem extends Component {
    static template = "website.EditWebsiteSystrayItem";
    static props = {
        onNewPage: { type: Function },
        onEditPage: { type: Function },
        iframeEl: { type: HTMLElement },
    };
    static components = {
        Dropdown,
        DropdownItem,
    };

    setup() {
        this.websiteService = useService("website");
        this.notification = useService("notification");
        this.websiteContext = useState(this.websiteService.context);
        // TODO: website service should share a reactive
        useBus(websiteSystrayRegistry, "CONTENT-UPDATED", () => this.checkPendingTranslations());
        this.isEnteringTranslateMode = false;
    }

    onClickEditPage() {
        this.websiteContext.edition = true;
        this.props.onEditPage();
    }

    get currentWebsiteInfo() {
        return this.websiteService.currentWebsite?.metadata;
    }

    get translatable() {
        return this.websiteService.currentWebsite?.metadata.translatable;
    }

    async attemptStartTranslate() {
        // TODO: move on the website part (not html_builder) and add a test tour
        if (this.websiteService.isRestrictedEditor && !this.websiteService.isDesigner) {
            const pageModelAndId = this.websiteService.currentWebsite.metadata.mainObject;
            const recordsOnPage = {
                [pageModelAndId.model]: pageModelAndId.id,
            };
            const otherRecordEls = this.props.iframeEl.querySelectorAll(
                "[data-res-model][data-res-id]:not([data-res-model='ir.ui.view']), [data-oe-model][data-oe-id]:not([data-oe-model='ir.ui.view'])"
            );
            for (const el of otherRecordEls) {
                const model = el.dataset.resModel || el.dataset.oeModel;
                if (!recordsOnPage[model]) {
                    // Keep one record of each type.
                    recordsOnPage[model] = parseInt(el.dataset.resId || el.dataset.oeId);
                }
            }
            await rpc("/website/check_can_modify_any", {
                records: Object.entries(recordsOnPage).map(([res_model, res_id]) => ({
                    res_model,
                    res_id,
                })),
            });
        }
        this.startTranslate();
    }

    getLocation() {
        return this.websiteService.contentWindow.location;
    }

    editFromTranslate() {
        // We are in translate mode, the pathname starts with '/<url_code>'. By
        // adding a trailing slash we can simply search for the first slash
        // after the language code to remove the language part.
        const { pathname, search, hash } = this.getLocation();
        const languagePrefix = `${pathname}/`.indexOf("/", 1);
        const defaultLanguagePathname = pathname.substring(languagePrefix);
        this.websiteService.goToWebsite({
            path: defaultLanguagePathname + search + hash,
            lang: "default",
            edition: true,
            htmlBuilder: true,
        });
    }

    startTranslate() {
        this.isEnteringTranslateMode = true;
        const { pathname, search, hash } = this.getLocation();
        const searchParams = new URLSearchParams(search);
        searchParams.set("edit_translations", "1");
        this.websiteService.goToWebsite({
            path: pathname + `?${searchParams.toString() + hash}`,
            translation: true,
            htmlBuilder: true,
        });
    }

    async checkPendingTranslations() {
        if (this.translatable && !this.isEnteringTranslateMode) {
            const { pathname, search, hash } = this.getLocation();
            const searchParams = new URLSearchParams(search);
            searchParams.set("edit_translations", "1");
            const path = pathname + `?${searchParams.toString() + hash}`;
            const response = await fetch(path);
            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, "text/html");
            if (doc.querySelector("#wrap .o_delay_translation")) {
                this.notification.add(
                    _t('Click on "Edit/Translate" to apply changes made on default language.'),
                    { type: "info" }
                );
            }
        }
        this.isEnteringTranslateMode = false;
    }
}
