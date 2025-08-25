/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import options from "@web_editor/js/editor/snippets.options";

options.registry.countdown = options.Class.extend({
    events: Object.assign({}, options.Class.prototype.events || {}, {
        'click .toggle-edit-message': '_onToggleEndMessageClick',
    }),

    /**
     * Remove any preview classes, if present.
     *
     * @override
     */
    cleanForSave: async function () {
        this.$target.find('.s_countdown_canvas_wrapper').removeClass("s_countdown_none");
        this.$target.find('.s_countdown_end_message').removeClass("s_countdown_enable_preview");
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the countdown action at zero.
     *
     * @see this.selectClass for parameters
     */
    endAction: function (previewMode, widgetValue, params) {
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
    },
    /**
    * Changes the countdown style.
    *
    * @see this.selectClass for parameters
    */
    layout: function (previewMode, widgetValue, params) {
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
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    updateUIVisibility: async function () {
        await this._super(...arguments);
        const dataset = this.$target[0].dataset;

        // End Action UI
        this.$el.find('.toggle-edit-message')
            .toggleClass('d-none', dataset.endAction === 'nothing' || dataset.endAction === 'redirect');

        // End Message UI
        this.updateUIEndMessage();
    },
    /**
     * @see this.updateUI
     */
    updateUIEndMessage: function () {
        this.$target.find('.s_countdown_canvas_wrapper')
            .toggleClass("s_countdown_none", this.showEndMessage === true && this.$target.hasClass("hide-countdown"));
        this.$target.find('.s_countdown_end_message')
            .toggleClass("s_countdown_enable_preview", this.showEndMessage === true);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'endAction':
            case 'layout':
                return this.$target[0].dataset[methodName];

            case 'selectDataAttribute': {
                if (params.colorNames) {
                    params.attributeDefaultValue = "rgba(0, 0, 0, 0)";
                }
                break;
            }
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onToggleEndMessageClick: function () {
        this.showEndMessage = !this.showEndMessage;
        this.$el.find(".toggle-edit-message")
            .toggleClass('text-primary', this.showEndMessage);
        this.updateUIEndMessage();
        this.trigger_up('cover_update');
    },
});
