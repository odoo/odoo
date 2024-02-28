odoo.define('web.special_fields', function (require) {
"use strict";

var core = require('web.core');
var field_utils = require('web.field_utils');
var relational_fields = require('web.relational_fields');
var AbstractField = require('web.AbstractField');

var FieldSelection = relational_fields.FieldSelection;
var _t = core._t;
var _lt = core._lt;


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
        if (!this.mismatch || !this.$option.html()) {
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
        var $span = $('<span class="fa fa-exclamation-triangle o_tz_warning"/>');

        if (this.$option && this.$option.html()) {
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
            $span.insertAfter(this.$el);
            if (this.nodeOptions.mismatch_title) {
                $span.attr('title', this.nodeOptions.mismatch_title);    
            }
            else {
                $span.attr('title', _t("Timezone Mismatch : This timezone is different from that of your browser.\nPlease, set the same timezone as your browser's to avoid time discrepancies in your system."));
            }
            this.$el = this.$el.add($span);

            this.$option = this.$('option').filter(function () {
                return $(this).attr('value') === value;
            });
            this._renderDateTimeTimezone();
        } else if (value == "false") {
            $span.insertAfter(this.$el);
            $span.attr('title', _t("Set a timezone on your user"));
            this.$el = this.$el.add($span);
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

const IframeWrapper = AbstractField.extend({
    description: _lt("Wrap raw html within an iframe"),

    // If HTML, don't forget to adjust the sanitize options to avoid stripping most of the metadata
    supportedFieldTypes: ['text', 'html'],

    template: "web.IframeWrapper",

    _render() {

        const spinner = this.el.querySelector('.o_iframe_wrapper_spinner');
        const iframe = this.el.querySelector('.o_preview_iframe');

        iframe.style.display = 'none';
        spinner.style.display = 'block';

        // Promise for tests
        let resolver;
        $(iframe).data('ready', new Promise((resolve) => {
            resolver = resolve;
        }));

        /**
         * Certain browser don't trigger onload events of iframe for particular cases.
         * In our case, chrome and safari could be problematic depending on version and environment.
         * This rather unorthodox solution replace the onload event handler. (jquery on('load') doesn't fix it)
         */
        const onloadReplacement = setInterval(() => {
            const iframeDoc = iframe.contentDocument;
            if (iframeDoc && (iframeDoc.readyState === 'complete' || iframeDoc.readyState === 'interactive')) {

                /**
                 * The document.write is not recommended. It is better to manipulate the DOM through $.appendChild and
                 * others. In our case though, we deal with an iframe without src attribute and with metadata to put in
                 * head tag. If we use the usual dom methods, the iframe is automatically created with its document
                 * component containing html > head & body. Therefore, if we want to make it work that way, we would
                 * need to receive each piece at a time to  append it to this document (with this.record.data and extra
                 * model fields or with an rpc). It also cause other difficulties getting attribute on the most parent
                 * nodes, parsing to HTML complex elements, etc.
                 * Therefore, document.write makes it much more trivial in our situation.
                 */
                iframeDoc.open();
                iframeDoc.write(this.value);
                iframeDoc.close();

                iframe.style.display = 'block';
                spinner.style.display = 'none';

                resolver();

                clearInterval(onloadReplacement);
            }
        }, 100);

    }

});


return {
    FieldTimezoneMismatch: FieldTimezoneMismatch,
    IframeWrapper,
};

});
