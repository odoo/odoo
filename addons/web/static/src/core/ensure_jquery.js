import { loadBundle } from "./assets";

export async function ensureJQuery() {
    if (!window.jQuery) {
        await loadBundle("web._assets_jquery");
        // allow to instantiate Bootstrap classes via jQuery: e.g. $(...).dropdown
        const BTS_CLASSES = ["Carousel", "Dropdown", "Modal", "Popover", "Tooltip", "Collapse"];
        const $ = window.jQuery;
        for (const CLS of BTS_CLASSES) {
            const plugin = window[CLS];
            if (plugin) {
                const name = plugin.NAME;
                const JQUERY_NO_CONFLICT = $.fn[name];
                $.fn[name] = plugin.jQueryInterface;
                $.fn[name].Constructor = plugin;
                $.fn[name].noConflict = () => {
                    $.fn[name] = JQUERY_NO_CONFLICT;
                    return plugin.jQueryInterface;
                };
            }
        }
    }
}
