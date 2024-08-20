/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import {
    SnippetOption,
} from "@web_editor/js/editor/snippets.options";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";

class Countdown extends SnippetOption {
    /**
     * Remove any preview classes, if present.
     *
     * @override
     */
    async cleanForSave() {
        this.$target.find('.s_countdown_canvas_wrapper').removeClass("s_countdown_none");
        this.$target.find('.s_countdown_end_message').removeClass("s_countdown_enable_preview");
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the countdown action at zero.
     *
     * @see this.selectClass for parameters
     */
    endAction(previewMode, widgetValue, params) {
        this.$target[0].dataset.endAction = widgetValue;
        if (widgetValue === 'message' || widgetValue === 'message_no_countdown') {
            if (!this.$target.find('.s_countdown_end_message').length) {
                const message = this.endMessage || renderToElement('website.s_countdown.end_message');
                this.$target.append(message);
            }
            this.$target.toggleClass('hide-countdown', widgetValue === 'message_no_countdown');
        } else {
            const $message = this.$target.find('.s_countdown_end_message').detach();
            if (this.showEndMessage) {
                this._onToggleEndMessageClick();
            }
            if ($message.length) {
                this.endMessage = $message[0].outerHTML;
            }
        }
    }
    /**
    * Changes the countdown style.
    *
    * @see this.selectClass for parameters
    */
    layout(previewMode, widgetValue, params) {
        switch (widgetValue) {
            case 'circle':
                this.$target[0].dataset.progressBarStyle = 'disappear';
                this.$target[0].dataset.progressBarWeight = 'thin';
                this.$target[0].dataset.layoutBackground = 'none';
                break;
            case 'boxes':
                this.$target[0].dataset.progressBarStyle = 'none';
                this.$target[0].dataset.layoutBackground = 'plain';
                break;
            case 'clean':
                this.$target[0].dataset.progressBarStyle = 'none';
                this.$target[0].dataset.layoutBackground = 'none';
                break;
            case 'text':
                this.$target[0].dataset.progressBarStyle = 'none';
                this.$target[0].dataset.layoutBackground = 'none';
                break;
        }
        this.$target[0].dataset.layout = widgetValue;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUIVisibility() {
        await super.updateUIVisibility(...arguments);
        // End Message UI
        this.updateUIEndMessage();
    }
    /**
     * @see this.updateUI
     */
    updateUIEndMessage() {
        this.$target.find('.s_countdown_canvas_wrapper')
            .toggleClass("s_countdown_none", this.showEndMessage === true && this.$target.hasClass("hide-countdown"));
        this.$target.find('.s_countdown_end_message')
            .toggleClass("s_countdown_enable_preview", this.showEndMessage === true);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'endAction':
            case 'layout':
                return this.$target[0].dataset[methodName];

            case 'selectDataAttribute': {
                if (params.colorNames) {
                    params.attributeDefaultValue = 'rgba(0, 0, 0, 255)';
                }
                break;
            }
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'show_message_opt') {
            const dataset = this.$target[0].dataset;
            return !['nothing', 'redirect'].includes(dataset.endAction);
        }
        return super._computeWidgetVisibility(...arguments);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    toggleEndMessage() {
        this.showEndMessage = !this.showEndMessage;
        this.updateUIEndMessage();
        this.callbacks.coverUpdate();
        this.renderContext.showEndMessage = this.showEndMessage;
    }
    /**
     * @override
     */
    async _getRenderContext() {
        return {
            showEndMessage: this.showEndMessage,
        };
    }
}

registerWebsiteOption("Countdown", {
    Class: Countdown,
    template: "website.s_countdown_option",
    selector: ".s_countdown",
});
