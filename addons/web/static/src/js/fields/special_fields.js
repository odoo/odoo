odoo.define('web.special_fields', function (require) {
"use strict";

var core = require('web.core');
var field_utils = require('web.field_utils');
var relational_fields = require('web.relational_fields');

var FieldSelection = relational_fields.FieldSelection;
var _t = core._t;


/**
 * This widget is intended to display a warning near a label of a 'timezone' field
 * indicating if the browser timezone is identical (or not) to the selected timezone.
 * This widget depends on a field given with the param 'tz_offset_field', which contains
 * the time difference between UTC time and local time, in minutes.
 */
var FieldTimezoneMismatch = FieldSelection.extend({
    /**
     * @override
     */
    start: function () {
        var interval = navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? 60000 : 1000;
        this._datetime = setInterval(this._renderDateTimeTimezone.bind(this), interval);
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        clearInterval(this._datetime);
        return this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        this._super.apply(this, arguments);
        this._renderTimezoneMismatch();
    },
    /**
     * Display the time in the user timezone (reload each second)
     *
     * @private
     */
    _renderDateTimeTimezone: function () {
        if (!this.mismatch) {
            return;
        }
        var offset = this.recordData.tz_offset.match(/([+-])([0-9]{2})([0-9]{2})/);
        offset = (offset[1] === '-' ? -1 : 1) * (parseInt(offset[2])*60 + parseInt(offset[3]));
        var datetime = field_utils.format.datetime(moment.utc().add(offset, 'minutes'), this.field, {timezone: false});
        var content = this.$option.html().split(' ')[0];
        content += '    ('+ datetime + ')';
        this.$option.html(content);
    },
    /**
     * Display the timezone alert
     * 
     * Note: timezone alert is a span that is added after $el, and $el is now a
     * set of two elements
     *
     * @private
     */
    _renderTimezoneMismatch: function () {
        // we need to clean the warning to have maximum one alert
        this.$el.last().filter('.o_tz_warning').remove();
        this.$el = this.$el.first();
        var value = this.$el.val();

        if (this.$option) {
            this.$option.html(this.$option.html().split(' ')[0]);
        }

        var userOffset = this.recordData.tz_offset;
        this.mismatch = false;
        if (userOffset && value !== "" && value !== "false") {
            var offset = -(new Date().getTimezoneOffset());
            var browserOffset = (offset < 0) ? "-" : "+";
            browserOffset += _.str.sprintf("%02d", Math.abs(offset / 60));
            browserOffset += _.str.sprintf("%02d", Math.abs(offset % 60));
            this.mismatch = (browserOffset !== userOffset);
        }

        if (this.mismatch){
            var $span = $('<span class="fa fa-exclamation-triangle o_tz_warning"/>');
            $span.insertAfter(this.$el);
            $span.attr('title', _t("Timezone Mismatch : The timezone of your browser doesn't match the selected one. The time in Odoo is displayed according to the timezone set on your user's preferences."));
            this.$el = this.$el.add($span);

            this.$option = this.$('option').filter(function () {
                return $(this).attr('value') === value;
            });
            this._renderDateTimeTimezone();
        }
    },
    /**
     * @override
     * @private
     * this.$el can have other elements than select
     * that should not be touched
     */
    _renderEdit: function () {
        // FIXME: hack to handle multiple root elements
        // in this.$el , which is a bad idea
        // In master we should make this.$el a wrapper
        // around multiple subelements
        var $otherEl = this.$el.not('select');
        this.$el = this.$el.first();

        this._super.apply(this, arguments);

        $otherEl.insertAfter(this.$el);
        this.$el = this.$el.add($otherEl);
    },
});

var FieldReportLayout = relational_fields.FieldMany2One.extend({
    // this widget is not generic, so we disable its studio use
    // supportedFieldTypes: ['many2one', 'selection'],
    events: _.extend({}, relational_fields.FieldMany2One.prototype.events, {
        'click img': '_onImgClicked',
    }),

    willStart: function () {
        var self = this;
        this.previews = {};
        return this._super()
            .then(function () {
                return self._rpc({
                    model: 'report.layout',
                    method: "search_read"
                }).then(function (values) {
                    self.previews = values;
                });
            });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        var self = this;
        this.$el.empty();
        var value = _.isObject(this.value) ? this.value.data.id : this.value;
        _.each(this.previews, function (val) {
            var $container = $('<div>').addClass('col-3 text-center');
            var $img = $('<img>')
                .addClass('img img-fluid img-thumbnail ml16')
                .toggleClass('btn-info', val.view_id[0] === value)
                .attr('src', val.image)
                .data('key', val.view_id[0]);
            $container.append($img);
            if (val.pdf) {
                var $previewLink = $('<a>')
                    .text('Preview')
                    .attr('href', val.pdf)
                    .attr('target', '_blank');
                $container.append($previewLink);
            }
            self.$el.append($container);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @param {MouseEvent} event
     */
    _onImgClicked: function (event) {
        this._setValue($(event.currentTarget).data('key'));
    },
});


return {
    FieldTimezoneMismatch: FieldTimezoneMismatch,
    FieldReportLayout: FieldReportLayout,
};

});
