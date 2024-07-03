/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { SnippetOption } from "@web_editor/js/editor/snippets.options";
import { registerWebsiteOption } from "@website/js/editor/snippets.registry";

class GoogleMap extends SnippetOption {

    /**
     * @override
     */
    async onBuilt(options) {
        this.env.gmapApiRequest({
            editableMode: true,
            configureIfNecessary: true,
            onSuccess: (key) => key,
        });
        await super.onBuilt(...arguments);
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    resetMapColor(previewMode, widgetValue, params) {
        this.$target[0].dataset.mapColor = '';
    }
    /**
     * @see this.selectClass for parameters
     */
    setFormattedAddress(previewMode, widgetValue, params) {
        this.$target[0].dataset.pinAddress = params.gmapPlace.formatted_address;
    }
    /**
     * @see this.selectClass for parameters
     */
    async showDescription(previewMode, widgetValue, params) {
        const descriptionEl = this.$target[0].querySelector('.description');
        if (widgetValue && !descriptionEl) {
            this.$target.append($(`
                <div class="description">
                    <font>${_t('Visit us:')}</font>
                    <span>${_t('Our office is located in the northeast of Brussels. TEL (555) 432 2365')}</span>
                </div>`)
            );
        } else if (!widgetValue && descriptionEl) {
            descriptionEl.remove();
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'showDescription') {
            return this.$target[0].querySelector('.description') ? 'true' : '';
        }
        return super._computeWidgetState(...arguments);
    }
}
registerWebsiteOption("GoogleMap", {
    Class: GoogleMap,
    template: "website.s_google_map_option",
    selector: ".s_google_map",
});
