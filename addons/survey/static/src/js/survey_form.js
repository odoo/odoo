odoo.define('survey.form.widget', function(require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var field_utils = require('web.field_utils');
var rpc = require('web.rpc');
var Widget = require('web.Widget');
var time = require('web.time');

var qweb = core.qweb;

var SurveyFormWidget = Widget.extend({
    template: false,
    events: {
        'change .o_survey_form_simple_radio input[type="radio"]': '_onChangeRadio',
        'change .o_survey_form_select': '_onChangeSelect',
        'change .o_survey_form_checkbox_other': '_onChangeMultipleCheckbox',
        'click button[type="submit"]': '_onSubmit',
    },


     //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

     /**
     * @override
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = _.defaults(options || {}, {
        });
        this.surveyId = this.options.surveyId;
        this.token = this.options.token;
        console.log('Initializing survey form with options', this.options);
    },

     /**
     * @override
     */
    start: function () {
        var self = this;

         _.each($('div.o_survey_form_date'), function (date_group) {
            self._updateDateForDisplay(date_group);
        });

         _.each($('div.o_survey_form_simple_select'), function (select_group) {
            self._updateSimpleSelectForDisplay($(select_group));
        });

         _.each($('div.o_survey_form_simple_radio'), function (radio_group) {
            self._updateSimpleRadioForDisplay($(radio_group));
        });

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onChangeRadio: function (event) {
        var $radio_group = $(event.currentTarget).parents('.o_survey_form_simple_radio');
        return this._updateSimpleRadioForDisplay($radio_group);
    },

    _onChangeSelect: function (event) {
        var $select_group = $(event.currentTarget).parents('.o_survey_form_simple_select');
        return this._updateSimpleSelectForDisplay($select_group);
    },

    _onChangeMultipleCheckbox: function (event) {
        var $elem = $(event.currentTarget);
        var $comment_input = $elem.parents('.o_survey_form_multiple').find('input[type="text"]');
        if ($elem.prop('checked')) {
            $comment_input.focus();
        }
        else {
            $comment_input.val('');
        }
    },

    _onSubmit: function (event) {
        var self = this;
        event.preventDefault();
        // event.stopPropagation();
        var $elem = $(event.currentTarget);
        var submitValue = $elem.val();
        var $form = $elem.parents('form.o_survey_form');
        var formData = $form.serializeArray();
        var params = {
            button_submit: submitValue,
        };
        _.each(formData, function (data, idx) {
            params[data.name] = data.value;
        });
        console.log('Submitting form', $elem, 'with params', params, 'to', $form.attr('action'));

        this._resetErrors();

        _.each($form.find('div.o_survey_form_date'), function (date_field) {
            self._updateDateForSubmit(date_field, params);
        });

        return rpc.query({
            route: '/survey/validate/' + self.surveyId + '/' + self.token,
            params: params,
        }).then(function (result) {
            console.log('-> form validation result', result);
            if (result === true) {
                var prout = $form.attr('action');
                if (submitValue === 'previous') {
                    prout += '?prev=prev';
                    $form.attr('action', prout)
                }
                $form.submit();
            }
            else if (result && result.fields && result.error === 'validation') {
                console.log('-> form validation error');
                _.each(_.keys(result.fields), function (key) {
                    $("#" + key + '>.js_errzone').append('<p>' + result.fields[key] + '</p>').show();
                });
                return false;
            }
            else {
                return false;
            }
        });
    },

     /**
     * Clean all form errors in order to clean DOM before a new validation
     */
    _resetErrors: function () {
        $('.js_errzone').html('').hide();
    },

    _updateDateForDisplay: function (date_group) {
        var input = $(date_group).find('input');
        var date_value = input.val() || '';

        // display dates in user timezone
        if (date_value) {
            var moment_date = field_utils.parse.date(date_value);
            date_value = field_utils.format.date(moment_date, null, {timezone: true});
        }
        console.log('Updating date for display:', date_group, ' value', input.val(), 'changed to', date_value);
        input.val(date_value);

        var minDate = $(date_group).data('mindate') || moment({ y: 1900 });
        var maxDate = $(date_group).data('maxdate') || moment().add(200, "y");
        $('#' + date_group.id).datetimepicker({
            format : time.getLangDateFormat(),
            minDate: minDate,
            maxDate: maxDate,
            calendarWeeks: true,
            icons: {
                time: 'fa fa-clock-o',
                date: 'fa fa-calendar',
                next: 'fa fa-chevron-right',
                previous: 'fa fa-chevron-left',
                up: 'fa fa-chevron-up',
                down: 'fa fa-chevron-down',
            },
            locale : moment.locale(),
            allowInputToggle: true,
            keyBinds: null,
        });
    },

    _updateDateForSubmit: function (date_group, params) {
        var input = $(date_group).find('input');
        var date_value = input.val();
        if (date_value) {
            var moment_date = moment(date_value);
            moment_date.toJSON = function () {
                return this.clone().locale('en').format('YYYY-MM-DD');
            };
            var server_date_value = JSON.parse(JSON.stringify(moment_date));
            params[input.attr('name')] = server_date_value;
            console.log('Updated before submit', date_value, 'to', server_date_value);
        }
    },

    _updateSimpleRadioForDisplay: function ($radio_group) {
        console.log('Updating simple radio:', $radio_group);

        var $other = $radio_group.find('.o_survey_form_radio_other');
        var $comment_input = $radio_group.find('input[type="text"]');
        if ($other.prop('checked')) {
            $comment_input.focus();
        }
        else {
            $comment_input.val('');
        }
    },

    _updateSimpleSelectForDisplay: function ($select_group) {
        console.log('Updating simple select:', $select_group);

        var $select = $select_group.find('select');
        var $other = $select_group.find('.o_survey_form_select_other');
        var $comment_input = $select_group.find('input[type="text"]');
        if ($select.val() === $other.val()) {
            $comment_input.show();
        }
        else {
            $comment_input.val('');
            $comment_input.hide();
        }
    },
});

return SurveyFormWidget;

});
