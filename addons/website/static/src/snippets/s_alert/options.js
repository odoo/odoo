import options from "@web_editor/js/editor/snippets.options";
import fonts from "@web_editor/js/wysiwyg/fonts";

options.registry.Alert = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes alert's icon pictogram.
     *
     * @see this.selectClass for parameters
     */
    selectAlertIcon(previewMode, widgetValue, params) {
        const alertIconEl = this.$target[0].querySelector(".s_alert_icon");
        if (!alertIconEl) {
            return;
        }

        // Note: this function is basically a "selectClass" combined with an
        // "applyTo" but each option already comes with a "selectClass"
        // targeting the main container. This is also why this does not need
        // a _computeWidgetState, relying on the "selectClass" one which comes
        // afterwards alphabetically (compared to "selectAlertIcon").
        fonts.computeFonts();
        let iconClass = widgetValue;
        const allFaIcons = fonts.fontIcons[0].alias;
        if (previewMode === "reset") {
            iconClass = this.initialIconClass;
        } else {
            this.initialIconClass = [...alertIconEl.classList].filter(
                (c) => allFaIcons.includes(c)
            );
        }
        alertIconEl.classList.remove(...allFaIcons);
        alertIconEl.classList.add(iconClass);
    },
});
