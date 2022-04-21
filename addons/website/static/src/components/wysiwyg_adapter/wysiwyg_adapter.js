/** @odoo-module */

import { ComponentAdapter } from 'web.OwlCompatibility';

import { useWowlService } from '@web/legacy/utils';


const { onWillStart, useEffect } = owl;

/**
 * This component adapts the Wysiwyg widget from @web_editor/wysiwyg.js.
 * In reality it encapsulate it so that this legacy widget can work in an OWL
 * framework.
 */
export class WysiwygAdapterComponent extends ComponentAdapter {
    /**
     * @override
     */
    setup() {
        super.setup();
        const options = this.props.options || {};

        this.websiteService = useWowlService('website');
        useEffect(() => {
            const initWysiwyg = async () => {

                if (this.props.snippetSelector) {
                    const snippetEl = $(this.websiteService.pageDocument).find(this.props.snippetSelector);
                    await this.widget.snippetsMenu.activateSnippet($(snippetEl));
                }

                this.props.wysiwygReady();
            };

            initWysiwyg();

        }, () => []);
    }
    /**
     * @override
     */
    get widgetArgs() {
        return [this._wysiwygParams];
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @return {Object} Params to pass to the wysiwyg widget.
     */
    get _wysiwygParams() {
        return {};
    }
}
