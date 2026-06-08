import { Plugin } from "@html_editor/plugin";
import { backgroundImageCssToParts, backgroundImagePartsToCss } from "@html_editor/utils/image";

/**
 * @typedef { Object } StyleShared
 * @property { StylePlugin['setBackgroundImageUrl'] } setBackgroundImageUrl
 */

export class StylePlugin extends Plugin {
    static id = "style";
    static shared = ["setBackgroundImageUrl"];

    setBackgroundImageUrl(el, value) {
        const parts = backgroundImageCssToParts(el.style["background-image"]);
        if (value) {
            parts.url = `url('${value}')`;
        } else {
            delete parts.url;
        }
        el.style["background-image"] = backgroundImagePartsToCss(parts);
    }
}
