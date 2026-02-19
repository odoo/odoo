import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";

export class LangChange extends Interaction {
    static selector = ".js_change_lang";
    dynamicContent = {
        _root: { "t-on-click.prevent.withTarget": this.onLangChangeClick },
    };

    onLangChangeClick(ev, el) {
        const lang = encodeURIComponent(el.dataset.url_code);
        const redirectURL = new URL(el.getAttribute("href"), window.location.origin);
        redirectURL.searchParams.delete("edit_translations");
        const url = encodeURIComponent(`${redirectURL.pathname}${redirectURL.search}`);
        const hash = encodeURIComponent(window.location.hash);
        redirect(`/website/lang/${lang}?r=${url}${hash}`);
    }
}

registry.category("public.interactions").add("website.lang_change", LangChange);
