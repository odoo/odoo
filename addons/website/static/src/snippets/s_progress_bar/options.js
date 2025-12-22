/** @odoo-module **/

import { clamp } from "@web/core/utils/numbers";
import options from "@web_editor/js/editor/snippets.options";

options.registry.progress = options.Class.extend({

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

        const progress = this.$target[0].querySelector(".progress");
        const progressValue = progress.getAttribute("aria-valuenow");
        let progressLabel = this.$target[0].querySelector('.s_progress_bar_text');

        if (!progressLabel && widgetValue !== 'none') {
            progressLabel = document.createElement('span');
            progressLabel.classList.add('s_progress_bar_text', 'small');
            progressLabel.textContent = progressValue + '%';
        }

        if (widgetValue === 'inline') {
            this.$target[0].querySelector('.progress-bar').appendChild(progressLabel);
        } else if (['below', 'after'].includes(widgetValue)) {
            progress.insertAdjacentElement('afterend', progressLabel);
        }

        // Temporary hide the label. It's effectively removed in cleanForSave
        // if the option is confirmed
        if (progressLabel) {
            progressLabel.classList.toggle('d-none', widgetValue === 'none');
        }
    },
    /**
     * Sets the progress bar value.
     *
     * @see this.selectClass for parameters
     */
    progressBarValue: function (previewMode, widgetValue, params) {
        let value = parseInt(widgetValue);
        value = clamp(value, 0, 100);
        const $progressBar = this.$target.find('.progress-bar');
        const $progressBarText = this.$target.find('.s_progress_bar_text');
        const progressMain = this.$target[0].querySelector(".progress");
        // Target precisely the XX% not only XX to not replace wrong element
        // eg 'Since 1978 we have completed 45%' <- don't replace 1978
        $progressBarText.text($progressBarText.text().replace(/[0-9]+%/, value + '%'));
        progressMain.setAttribute('aria-valuenow', value);
        $progressBar.css("width", value + "%");
    },
    /**
     * @override
     */
    async cleanForSave() {
        const progressBar = this.$target[0].querySelector(".progress-bar");
        const progressLabel = this.$target[0].querySelector(".s_progress_bar_text");

        if (!progressBar.classList.contains('progress-bar-striped')) {
            progressBar.classList.remove('progress-bar-animated');
        }

        if (progressLabel && progressLabel.classList.contains('d-none')) {
            progressLabel.remove();
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
            case 'progressBarValue': {
                return this.$target[0].querySelector(".progress").getAttribute("aria-valuenow") + "%";
            }
        }
        return this._super(...arguments);
    },
});
