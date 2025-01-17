import { patch } from "@web/core/utils/patch";
import { Animation } from "@website/interactions/animation";

patch(Animation.prototype, {
    /**
     * @override
     * @todo This should be avoided: the natural scrollbar of the browser should
     * always be preferred. Indeed, moving the main scroll of the page to a
     * different location causes a lot of issues. See 189a7c96e6e26825dc05c0c64
     * for more information (improvement of 18.0 for general scrolling behaviors
     * in all website pages). E.g. issue in eLearning: go to an article in full
     * screen mode, try to use the up/down arrow keys to scroll: it does not
     * work (you first have to focus the article which should not be needed as
     * it is the only main scrollable element of the page).
     */
    findScrollingElement() {
        const articleContent = document.querySelector(".o_wslide_fs_article_content");
        return articleContent ? articleContent : super.findScrollingElement(...arguments);
    },
});
