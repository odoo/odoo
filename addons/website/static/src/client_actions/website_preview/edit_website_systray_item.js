/** @odoo-module native */
import { Component, useState } from "@odoo/owl";
import { Dropdown, DropdownItem } from "@web/components/dropdown";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { useBus, useService } from "@web/core/utils/hooks";

const websiteSystrayRegistry = registry.category("website_systray");

const log = makeLogger("website.systray.edit_website");

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
        useLifecycleLog(log);
        this.websiteService = useService("website");
        this.notification = useService("notification");
        this.websiteContext = useState(this.websiteService.context);
        useBus(websiteSystrayRegistry, "CONTENT-UPDATED", () =>
            this.checkPendingTranslations(),
        );
        this.isEnteringTranslateMode = false;
    }

    onClickEditPage() {
        log.logic("onClickEditPage");
        this.websiteContext.edition = true;
        this.props.onEditPage();
    }

    onEditDropdownClick() {
        this.closeNotification?.();
    }

    get currentWebsiteInfo() {
        return this.websiteService.currentWebsite?.metadata;
    }

    get translatable() {
        return this.websiteService.currentWebsite?.metadata.translatable;
    }

    async attemptStartTranslate() {
        if (this.websiteService.isRestrictedEditor && !this.websiteService.isDesigner) {
            const pageModelAndId =
                this.websiteService.currentWebsite.metadata.mainObject;
            const recordsOnPage = {
                [pageModelAndId.model]: pageModelAndId.id,
            };
            const endScan = log.perf("attemptStartTranslate scan records");
            const otherRecordEls = this.props.iframeEl.querySelectorAll(
                "[data-res-model][data-res-id]:not([data-res-model='ir.ui.view']), [data-oe-model][data-oe-id]:not([data-oe-model='ir.ui.view'])",
            );
            for (const el of otherRecordEls) {
                const model = el.dataset.resModel || el.dataset.oeModel;
                if (!recordsOnPage[model]) {
                    recordsOnPage[model] = parseInt(
                        el.dataset.resId || el.dataset.oeId,
                    );
                }
            }
            endScan(() => ({ elements: otherRecordEls.length }));
            const endCheck = log.perf("check_can_modify_any", () => ({
                models: Object.keys(recordsOnPage),
            }));
            await rpc("/website/check_can_modify_any", {
                records: Object.entries(recordsOnPage).map(([res_model, res_id]) => ({
                    res_model,
                    res_id,
                })),
            });
            endCheck();
        }
        this.startTranslate();
    }

    getLocation() {
        return this.websiteService.contentWindow.location;
    }

    editFromTranslate() {
        const { pathname, search, hash } = this.getLocation();
        const languagePrefix = `${pathname}/`.indexOf("/", 1);
        const defaultLanguagePathname = pathname.substring(languagePrefix);
        log.logic("editFromTranslate", { pathname, defaultLanguagePathname });
        this.websiteService.goToWebsite({
            path: defaultLanguagePathname + search + hash,
            lang: "default",
            edition: true,
        });
    }

    startTranslate() {
        log.logic("startTranslate");
        this.isEnteringTranslateMode = true;
        const { pathname, search, hash } = this.getLocation();
        const searchParams = new URLSearchParams(search);
        searchParams.set("edit_translations", "1");
        this.websiteService.goToWebsite({
            path: pathname + `?${searchParams.toString() + hash}`,
            translation: true,
        });
    }

    async checkPendingTranslations() {
        log.logic("checkPendingTranslations", () => ({
            translatable: Boolean(this.translatable),
            entering: this.isEnteringTranslateMode,
        }));
        if (this.translatable && !this.isEnteringTranslateMode) {
            const { pathname, search, hash } = this.getLocation();
            const searchParams = new URLSearchParams(search);
            searchParams.set("edit_translations", "1");
            const path = pathname + `?${searchParams.toString() + hash}`;
            const endFetch = log.perf("checkPendingTranslations fetch+parse", {
                path,
            });
            const response = await fetch(path);
            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, "text/html");
            endFetch(() => ({ bytes: html.length }));
            if (doc.querySelector("#wrap .o_delay_translation")) {
                log.logic("checkPendingTranslations: delayed translations found");
                this.closeNotification = this.notification.add(
                    _t(
                        'Click on "Edit/Translate" to apply changes made on default language.',
                    ),
                    { type: "info" },
                );
            }
        }
        this.isEnteringTranslateMode = false;
    }
}
