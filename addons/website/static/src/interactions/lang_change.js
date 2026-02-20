import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class LangChange extends Interaction {
    static selector = ".js_change_lang";
    dynamicContent = {
        _root: { "t-on-click.prevent.withTarget": this.onLangChangeClick },
    };

    onLangChangeClick(ev, el) {
        const lang = encodeURIComponent(el.dataset.url_code);
        const redirect = new URL(el.getAttribute("href"), window.location.origin);
        redirect.searchParams.delete("edit_translations");
        const url = encodeURIComponent(`${redirect.pathname}${redirect.search}`);
        const hash = encodeURIComponent(window.location.hash);
        window.location.href = `/website/lang/${lang}?r=${url}${hash}`;
    }
}

registry.category("public.interactions").add("website.lang_change", LangChange);
