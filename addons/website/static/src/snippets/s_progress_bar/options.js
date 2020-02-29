odoo.define('website.s_progress_bar_options', function (require) {
'use strict';

const core = require('web.core');
const options = require('web_editor.snippets.options');

const _t = core._t;

options.registry.progress = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        if (this.$overlay) {
            this._bindMoveProgress();
        }
        this._super();
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the position of the progressbar text.
     *
     * @see this.selectClass for parameters
     */
    display: function (previewMode, widgetValue, params) {
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
        }
        return this._super(...arguments);
    },
    /**
     * Binds the editor padding feature to the progress bar width.
     */
    _bindMoveProgress: function () {
        var self = this;
        var $e = this.$overlay.find(".o_handle.e").removeClass("readonly");
        const $progressBar = this.$target.find('.progress-bar');
        const $parent = $progressBar.parent();
        var pos = $parent.offset();
        var width = $parent.width();
        var time;
        function move(event) {
            clearTimeout(time);
            time = setTimeout(function () {
                var value = (event.clientX - pos.left) / width * 100 | 0;
                if (value > 100) {
                    value = 100;
                }
                if (value < 0) {
                    value = 0;
                }
                const $progressBarText = self.$target.find('.s_progress_bar_text');
                // Target precisely the XX% not only XX to not replace wrong element
                // eg 'Since 1978 we have completed 45%' <- don't replace 1978
                $progressBarText.text($progressBarText.text().replace(/[0-9]+%/, value + '%'));
                $progressBar.attr("data-value", value);
                $progressBar.attr("aria-valuenow", value);
                if (value < 3) {
                    value = 3;
                }
                $progressBar.css("width", value + "%");
            }, 5);
        }
        $e.on("mousedown", function () {
            self.$overlay.addClass('d-none');
            $(document)
                .on("mousemove", move)
                .one("mouseup", function () {
                    self.$overlay.removeClass('d-none');
                    $(document).off("mousemove", move);
                    self.trigger_up('cover_update');
                });
        });
    },
});
});
