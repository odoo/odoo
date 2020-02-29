odoo.define('mrp.mrp_state', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fields = require('web.basic_fields');
var field_registry = require('web.field_registry');
var time = require('web.time');

var _t = core._t;

/**
 * This widget is used to display the availability on a workorder.
 */
var SetBulletStatus = AbstractField.extend({
    // as this widget is based on hardcoded values, use it in another context
    // probably won't work
    // supportedFieldTypes: ['selection'],
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.classes = this.nodeOptions && this.nodeOptions.classes || {};
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _renderReadonly: function () {
        this._super.apply(this, arguments);
        var bullet_class = this.classes[this.value] || 'default';
        if (this.value) {
            var title = this.value === 'waiting' ? _t('Waiting Materials') : '';
            this.$el.attr({'title': title, 'style': 'display:inline'});
            this.$el.removeClass('text-success text-danger text-default');
            this.$el.html($('<span>' + title + '</span>').addClass('badge badge-' + bullet_class));
        }
    }
});

var TimeCounter = AbstractField.extend({
    supportedFieldTypes: [],
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var def = this._rpc({
            model: 'mrp.workcenter.productivity',
            method: 'search_read',
            domain: [
                ['workorder_id', '=', this.record.data.id],
            ],
        }).then(function (result) {
            if (self.mode === 'readonly') {
                var currentDate = new Date();
                self.duration = 0;
                _.each(result, function (data) {
                    self.duration += data.date_end ?
                        self._getDateDifference(data.date_start, data.date_end) :
                        self._getDateDifference(time.auto_str_to_date(data.date_start), currentDate);
                });
            }
        });
        return Promise.all([this._super.apply(this, arguments), def]);
    },

    destroy: function () {
        this._super.apply(this, arguments);
        clearTimeout(this.timer);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    isSet: function () {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Compute the difference between two dates.
     *
     * @private
     * @param {string} dateStart
     * @param {string} dateEnd
     * @returns {integer} the difference in millisecond
     */
    _getDateDifference: function (dateStart, dateEnd) {
        return moment(dateEnd).diff(moment(dateStart));
    },
    /**
     * @override
     */
    _render: function () {
        this._startTimeCounter();
    },
    /**
     * @private
     */
    _startTimeCounter: function () {
        var self = this;
        clearTimeout(this.timer);
        if (this.record.data.is_user_working) {
            this.timer = setTimeout(function () {
                self.duration += 1000;
                self._startTimeCounter();
            }, 1000);
        } else {
            clearTimeout(this.timer);
        }
        this.$el.html($('<span>' + moment.utc(this.duration).format("HH:mm:ss") + '</span>'));
    },
});

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
            this.setElement(this.$el.wrap('<div class="o_embed_url_viewer o_field_widget"/>').parent());
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
            this.$el.addClass('o_embed_url_viewer');
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
        $iframe.toggleClass('d-none', !src);
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


field_registry
    .add('bullet_state', SetBulletStatus)
    .add('mrp_time_counter', TimeCounter)
    .add('embed_viewer', FieldEmbedURLViewer);

return FieldEmbedURLViewer;
});
