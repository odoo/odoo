/** @odoo-module **/

import fields from 'web.basic_fields';
import field_registry from 'web.field_registry';

var FieldEmbedURLViewer = fields.FieldChar.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.page = 1;
        this.srcDirty = false;
    },

    /**
     * force to set 'src' for embed iframe viewer when its value has changed
     *
     * @override
     *
     */
    reset: function () {
        this._super.apply(this, arguments);
        this._updateIframePreview();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Initializes and returns an iframe for the viewer
     *
     * @private
     * @returns {jQueryElement}
     */
    _prepareIframe: function () {
        return $('<iframe>', {
            class: 'o_embed_iframe d-none',
            allowfullscreen: true,
        });
    },

    /**
     * @override
     * @private
     */
    _renderEdit: function () {
        if (!this.$('iframe.o_embed_iframe').length) {
            this.$input = this.$el;
            this.setElement(this.$el.wrap('<div class="o_embed_url_viewer o_field_widget w-100"/>').parent());
            this.$el.append(this._prepareIframe());
        }
        this._prepareInput(this.$input);

        // Do not set iframe src if widget is invisible
        if (!this.record.evalModifiers(this.attrs.modifiers).invisible) {
            this._updateIframePreview();
        } else {
            this.srcDirty = true;
        }
    },
    /**
     * @override
     * @private
     */
    _renderReadonly: function () {
        if (!this.$('iframe.o_embed_iframe').length) {
            this.$el.addClass('o_embed_url_viewer w-100');
            this.$el.append(this._prepareIframe());
        }
        this._updateIframePreview();
    },
    /**
     * Set the associated src for embed iframe viewer
     *
     * @private
     * @returns {string} source of the google slide
     */
    _getEmbedSrc: function () {
        var src = false;
        if (this.value) {
            // check given google slide url is valid or not
            var googleRegExp = /(^https:\/\/docs.google.com).*(\/d\/e\/|\/d\/)([A-Za-z0-9-_]+)/;
            var google = this.value.match(googleRegExp);
            if (google && google[3]) {
                src = 'https://docs.google.com/presentation' + google[2] + google[3] + '/preview?slide=' + this.page;
            }
        }
        return src || this.value;
    },
    /**
     * update iframe attrs
     *
     * @private
     */
    _updateIframePreview: function () {
        var $iframe = this.$('iframe.o_embed_iframe');
        var src = this._getEmbedSrc();
        $iframe.addClass('w-100 border-0').toggleClass('d-none', !src);
        if (src) {
            $iframe.attr('src', src);
        } else {
            $iframe.removeAttr('src');
        }
    },
    /**
     * Listen to modifiers updates to and only render iframe when it is necessary
     *
     * @override
     */
    updateModifiersValue: function () {
        this._super.apply(this, arguments);
        if (!this.attrs.modifiersValue.invisible && this.srcDirty) {
            this._updateIframePreview();
            this.srcDirty = false;
        }
    },
});

field_registry.add('embed_viewer', FieldEmbedURLViewer);

export default FieldEmbedURLViewer;
