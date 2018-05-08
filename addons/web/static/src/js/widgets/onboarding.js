odoo.define('web.onboarding', function (require) {
'use strict';

var core = require('web.core');
var Widget = require('web.Widget');
var Dialog = require('web.Dialog');

var _t = core._t;


var Onboarding = Widget.extend({
    template: 'web.onboarding',
    events: {
        'click .o_onboarding_btn_fold': '_toggleFold',
        'click .o_onboarding_btn_close': '_confirmClose',
        'click .o_onboarding_btn_completed': '_closeOnboarding',
    },

    start: function() {
        var self = this;
        var steps = this.$el.find('.o_onboarding_step');
        $(steps[0]).addClass('o_onboarding_current');

        _.each(steps, function(step, index) {
            $(step).find('.o_onboarding_step_action').on('click', function(){
                self._openFakeModal(step, index, steps);
            });
        });
    },

    _openFakeModal: function (step, index, steps) {
        var self = this;
        var dialog = new Dialog(this, {
            title: _t("Perform some actions"),
            $content: $('\
            <form class="form-horizontal">\
              <div class="form-group">\
                <label class="col-sm-2 control-label" for="exampleInputEmail1">Some data</label>\
                <div class="col-sm-10">\
                    <input type="text" class="form-control" id="text1" placeholder="Some data">\
                </div>\
              </div>\
              <div class="form-group">\
                <label class="col-sm-2 control-label" for="exampleInputPassword1">Some data</label>\
                <div class="col-sm-10">\
                    <input type="text2" class="form-control" id="text2" placeholder="Some data">\
                </div>\
              </div>\
              <div class="form-group">\
                <div class="col-sm-offset-2 col-sm-10">\
                    <label for="exampleInputFile">File input</label>\
                    <input type="file" id="exampleInputFile">\
                    <p class="help-block">Example block-level help text here.</p>\
                </div>\
            </form>\
            '),
            size: 'medium',
            buttons: [
                {text: _t("Apply changes"), classes: 'btn-primary pull-right', close: true, click: function () {
                    self._nextStep(step, index, steps);
                    dialog.destroy();
                }},
                {text: _t("Maybe later..."), close: true},
            ],
        });
        dialog.open();
    },

    _nextStep: function (step, index, steps) {
        var self = this;

        $(step).removeClass('o_onboarding_current').addClass('o_onboarding_done o_onboarding_clickable').on('click', function () {
            self._prevStep(step, index, steps);
        });

        if (index + 1 == steps.length ) {
            // Onboarding completed
            this.$el.addClass('o_onboarding_completed');
        } else {
            $(steps).not('.o_onboarding_done').first().addClass('o_onboarding_current')
        }
    },

    _prevStep: function (step, index, steps) {
        $(step).removeClass('o_onboarding_done').addClass('o_onboarding_current')
            .nextAll().removeClass('o_onboarding_current');
        this._openFakeModal(step, index, steps);
    },

    _toggleFold: function () {
        this.$el.toggleClass('o_onboarding_folded');
    },

    _confirmClose: function () {
        var self = this;
        var dialog = new Dialog(this, {
            title: _t("Close the configuration wizard?"),
            $content: $('\
            <div>\
                <p>You can always re-open the wizard:</p>\
                <b>Configuration</b> > <b>Open Onboarding</b>\
            </div>\
            '),
            size: 'medium',
            buttons: [
                {text: _t("Yes, close it"), classes: 'btn-primary pull-right', close: true, click: function () {
                    self._closeOnboarding();
                }},
                {text: _t("Cancel"), close: true},
            ],
        });
        dialog.open();
    },

    _closeOnboarding: function () {
        var self = this;
        this.$el.css('max-height', 0);

        setTimeout (function () {
            // let perform the css transition before destroy the wizard
            self.destroy();
        }, 1000);
    }
});

return Onboarding;

});
