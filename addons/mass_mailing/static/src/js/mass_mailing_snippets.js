odoo.define('mass_mailing.snippets.options', function (require) {
"use strict";

var options = require('web_editor.snippets.options');
const {ColorpickerWidget} = require('web.Colorpicker');
const {_t} = require('web.core');

// Adding compatibility for the outlook compliance of mailings.
// Commit of such compatibility : a14f89c8663c9cafecb1cc26918055e023ecbe42
options.registry.BackgroundImage = options.registry.BackgroundImage.extend({
    start: function () {
        this._super();
        if (this.snippets && this.snippets.split('.')[0] === "mass_mailing") {
            var $table_target = this.$target.find('table:first');
            if ($table_target.length) {
                this.$target = $table_target;
            }
        }
    }
});

options.registry.ImageTools.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUIVisibility() {
        await this._super(...arguments);

        // The image shape option should work correctly with this update of the
        // ImageTools option but unfortunately, SVG support in mail clients
        // prevents the final rendering of the image. For now, we disable the
        // feature.
        const imgShapeContainerEl = this.el.querySelector('.o_we_image_shape');
        if (imgShapeContainerEl) {
            imgShapeContainerEl.classList.toggle('d-none', !odoo.debug);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getCSSColorValue(color) {
        const doc = this.options.document;
        if (doc && doc.querySelector('.o_mass_mailing_iframe') && !ColorpickerWidget.isCSSColor(color)) {
            const tempEl = doc.body.appendChild(doc.createElement('div'));
            tempEl.className = `bg-${color}`;
            const colorValue = window.getComputedStyle(tempEl).getPropertyValue("background-color").trim();
            tempEl.parentNode.removeChild(tempEl);
            return ColorpickerWidget.normalizeCSSColor(colorValue).replace(/"/g, "'");
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _renderCustomWidgets(uiFragment) {
        await this._super(...arguments);

        const imgShapeTitleEl = uiFragment.querySelector('.o_we_image_shape we-title');
        if (imgShapeTitleEl) {
            const warningEl = document.createElement('i');
            warningEl.classList.add('fa', 'fa-exclamation-triangle', 'ml-1');
            warningEl.title = _t("Be aware that this option may not work on many mail clients");
            imgShapeTitleEl.appendChild(warningEl);
        }
    },
});

});
