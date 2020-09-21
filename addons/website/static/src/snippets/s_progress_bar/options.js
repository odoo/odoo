odoo.define('website.s_progress_bar_options', function (require) {
'use strict';

const core = require('web.core');
const utils = require('web.utils');
const snippetOptions = require('web_editor.snippets.options');

const _t = core._t;

snippetOptions.registry.progress = snippetOptions.SnippetOptionWidget.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the position of the progressbar text.
     *
     * @see this.selectClass for parameters
     */
    display: async function (previewMode, widgetValue, params) {
        // retro-compatibility
        if (this.$target.hasClass('progress')) {
            this.$target.removeClass('progress');
            this.$target.find('.progress-bar').wrap($('<div/>', {
                class: 'progress',
            }));
            this.$target.find('.progress-bar span').addClass('s_progress_bar_text');
        }

        let $text = this.$target.find('.s_progress_bar_text');
        if (!$text.length) {
            $text = $('<span/>').addClass('s_progress_bar_text').html(_t('80% Development'));
        }

        if (widgetValue === 'inline') {
            $text.appendTo(this.$target.find('.progress-bar'));
        } else {
            $text.insertBefore(this.$target.find('.progress'));
        }

        if (previewMode === false) await this._updateChangesInWysiwyg();
    },
    /**
     * Sets the progress bar value.
     *
     * @see this.selectClass for parameters
     */
    progressBarValue: async function (previewMode, widgetValue, params) {
        let value = parseInt(widgetValue);
        value = utils.confine(value, 0, 100);
        const $progressBar = this.$target.find('.progress-bar');
        const $progressBarText = this.$target.find('.s_progress_bar_text');
        // Target precisely the XX% not only XX to not replace wrong element
        // eg 'Since 1978 we have completed 45%' <- don't replace 1978
        $progressBarText.text($progressBarText.text().replace(/[0-9]+%/, value + '%'));
        $progressBar.attr("aria-valuenow", value);
        $progressBar.css("width", value + "%");

        if (previewMode === false) await this._updateChangesInWysiwyg();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'display': {
                const isInline = this.$target.find('.s_progress_bar_text')
                                        .parent('.progress-bar').length;
                return isInline ? 'inline' : 'below';
            }
            case 'progressBarValue': {
                return this.$target.find('.progress-bar').attr('aria-valuenow') + '%';
            }
        }
        return this._super(...arguments);
    },
});
});
