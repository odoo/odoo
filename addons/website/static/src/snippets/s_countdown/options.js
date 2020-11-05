odoo.define('website.s_countdown_options', function (require) {
'use strict';

const core = require('web.core');
const snippetOptions = require('web_editor.snippets.options');
const CountdownWidget = require('website.s_countdown');

const qweb = core.qweb;

snippetOptions.registry.countdown = snippetOptions.SnippetOptionWidget.extend({
    events: _.extend({}, snippetOptions.SnippetOptionWidget.prototype.events || {}, {
        'click .toggle-edit-message': '_onToggleEndMessageClick',
    }),

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the countdown action at zero.
     *
     * @see this.selectClass for parameters
     */
    endAction: async function (previewMode, widgetValue, params) {
        const countdownEndAction = async (context) => {
            await this.editorHelpers.setAttribute(context, this.$target[0], `data-end-action`, widgetValue);
            if (widgetValue === 'message' || widgetValue === 'message_no_countdown') {
                if (!this.$target.find('.s_countdown_end_message').length) {
                    const message = this.endMessage || qweb.render('website.s_countdown.end_message');
                    await this.editorHelpers.insertHtml(context, message, this.$target.find('.container')[0], 'INSIDE');
                    await this.editorHelpers.setClass(this.wysiwyg.editor, this.$target, 'flex-row-reverse flex-row', widgetValue === 'message_no_countdown');
                }
            } else {
                const $message = this.$target.find('.s_countdown_end_message');
                if ($message.length) {
                    this.endMessage = $message[0].outerHTML;
                }
                await this.editorHelpers.remove(context, $message[0]);
            }
        };
        await this.wysiwyg.editor.execCommand(countdownEndAction);
    },
    /**
    * Changes the countdown style.
    *
    * @see this.selectClass for parameters
    */
    layout: async function (previewMode, widgetValue, params) {
            switch (widgetValue) {
                case 'circle':
                    if (!previewMode) {
                        const countdownLayoutCircle = async (context) => {
                            await this.editorHelpers.setAttribute(context, this.$target[0], 'data-progress-bar-style', 'disappear');
                            await this.editorHelpers.setAttribute(context, this.$target[0], 'data-progress-bar-weight', 'thin');
                            await this.editorHelpers.setAttribute(context, this.$target[0], 'data-layout-background', 'none');
                            await this.editorHelpers.setAttribute(context, this.$target[0], 'data-layout', widgetValue);
                        };
                        await this.editor.execCommand(countdownLayoutCircle);
                    } else {
                        this.$target[0].dataset.progressBarStyle = 'disappear';
                        this.$target[0].dataset.progressBarWeight = 'thin';
                        this.$target[0].dataset.layoutBackground = 'none';
                    }
                    break;
                case 'boxes':
                    if (!previewMode) {
                        const countdownLayoutBoxes = async (context) => {
                            await this.editorHelpers.setAttribute(context, this.$target[0], 'data-progress-bar-style', 'none');
                            await this.editorHelpers.setAttribute(context, this.$target[0], 'data-layout-background', 'plain');
                            await this.editorHelpers.setAttribute(context, this.$target[0], 'data-layout', widgetValue);
                        };
                        await this.editor.execCommand(countdownLayoutBoxes);
                    } else {
                        this.$target[0].dataset.progressBarStyle = 'none';
                        this.$target[0].dataset.layoutBackground = 'plain';
                    }
                    break;
                case 'clean':
                    if (!previewMode) {
                        const countdownLayoutClean = async (context) => {
                            await this.editorHelpers.setAttribute(context, this.$target[0], 'data-progress-bar-style', 'none');
                            await this.editorHelpers.setAttribute(context, this.$target[0], 'data-layout-background', 'none');
                            await this.editorHelpers.setAttribute(context, this.$target[0], 'data-layout', widgetValue);
                        };
                        await this.editor.execCommand(countdownLayoutClean);
                    } else {
                        this.$target[0].dataset.progressBarStyle = 'none';
                        this.$target[0].dataset.layoutBackground = 'none';
                    }
                    break;
                case 'text':
                    if (!previewMode) {
                        const countdownLayoutText = async (context) => {
                            await this.editorHelpers.setAttribute(context, this.$target[0], 'data-progress-bar-style', 'none');
                            await this.editorHelpers.setAttribute(context, this.$target[0], 'data-layout-background', 'none');
                            await this.editorHelpers.setAttribute(context, this.$target[0], 'data-layout', widgetValue);
                        };
                        await this.editor.execCommand(countdownLayoutText);
                    } else {
                        this.$target[0].dataset.progressBarStyle = 'none';
                        this.$target[0].dataset.layoutBackground = 'none';
                    }
                    break;
                default:
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
            .toggleClass("d-none", this.showEndMessage === true && this.$target.hasClass("hide-countdown"));
        this.$target.find('.s_countdown_end_message')
            .toggleClass("d-none", !this.showEndMessage);
    },

    /**
     * @override
     */
    async cleanForSave() {
        this.$('.s_countdown_anvas_wrapper canvas').remove();
        await this.updateChangesInWysiwyg();
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
                    // In this case, it is a colorpicker controlling a data
                    // value on the countdown: the default value is determined
                    // by the countdown public widget.
                    params.attributeDefaultValue = CountdownWidget.prototype.defaultColor;
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
});
