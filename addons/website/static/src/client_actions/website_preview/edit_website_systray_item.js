import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { rpc } from "@web/core/network/rpc";

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
        this.websiteContext = useState(this.websiteService.context);
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
        const { pathname, search, hash } = this.getLocation();
        const searchParams = new URLSearchParams(search);
        searchParams.set("edit_translations", "1");
        this.websiteService.goToWebsite({
            path: pathname + `?${searchParams.toString() + hash}`,
            translation: true,
            htmlBuilder: true,
        });
    }
}
