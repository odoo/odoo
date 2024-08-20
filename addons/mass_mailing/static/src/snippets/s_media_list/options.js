import { SnippetOption } from "@web_editor/js/editor/snippets.options";

// FIXME: this is unused (no option definition in mass_mailing),
//  see addons/website/static/src/snippets/s_media_list/options.js
//  This is never attached to any snippet (no selector).
export class MediaItemLayout extends SnippetOption {

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Change the media item layout.
     *
     * @see this.selectClass for parameters
     */
    layout(previewMode, widgetValue, params) {
        const $image = this.$target.find('.s_media_list_img_wrapper');
        const $content = this.$target.find('.s_media_list_body');

        for (const possibleValue of params.possibleValues) {
            $image.removeClass(`col-lg-${possibleValue}`);
            $content.removeClass(`col-lg-${12 - possibleValue}`);
        }
        $image.addClass(`col-lg-${widgetValue}`);
        $content.addClass(`col-lg-${12 - widgetValue}`);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'layout': {
                const $image = this.$target.find('.s_media_list_img_wrapper');
                for (const possibleValue of params.possibleValues) {
                    if ($image.hasClass(`col-lg-${possibleValue}`)) {
                        return possibleValue;
                    }
                }
            }
        }
        return super._computeWidgetState(...arguments);
    }
}
