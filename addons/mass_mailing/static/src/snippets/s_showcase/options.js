import { SnippetOption } from "@web_editor/js/editor/snippets.options";

// FIXME: this is unused (no option definition in mass_mailing),
//  see addons/website/static/src/snippets/s_showcase/options.js
//  This is never attached to any snippet (no selector). Even if
//  it was, it is impossible to move Showcase sub-elements (that start
//  with a title and an icon), and it would therefor have no effect.
export class Showcase extends SnippetOption {
    /**
     * @override
     */
    onMove() {
        const $showcaseCol = this.$target.parent().closest('.row > div');
        const isLeftCol = $showcaseCol.index() <= 0;
        const $title = this.$target.children('.s_showcase_title');
        $title.toggleClass('flex-lg-row-reverse', isLeftCol);
        $showcaseCol.find('.s_showcase_icon.ms-3').removeClass('ms-3').addClass('ms-lg-3'); // For compatibility with old version
        $title.find('.s_showcase_icon').toggleClass('me-lg-0 ms-lg-3', isLeftCol);
    }
}
