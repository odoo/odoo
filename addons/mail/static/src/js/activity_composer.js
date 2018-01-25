odoo.define('mail.ActivityComposer', function (require) {
"use strict";

var basic_fields = require('web.basic_fields');
var core = require('web.core');
var relational_fields = require('web.relational_fields');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var Widget = require('web.Widget');

var _t = core._t;

var ActivityComposer = Widget.extend(StandaloneFieldManagerMixin, {
    template: 'mail.ActivityComposer',
    events: {
        'click .o_schedule_activity': '_onScheduleActivity',
        'click .o_activity_full_composer_btn': '_onEditActivity'
    },
    /**
     * @override
     * @param {widget} parent
     * @param {Object} form_record record of the currently loaded form view
     */
    init: function (parent, form_record) {
        this._super(parent);
        StandaloneFieldManagerMixin.init.call(this);
        this.res_id = form_record.res_id;
        this.res_model = form_record.model;
        this.fields = {};
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var fields = this._getFileds();
        return this.model.load({
            fields: fields,
            fieldsInfo: {
                default: fields
            },
            modelName: 'mail.activity',
            type: 'record',
            context: {
                default_res_id: this.res_id,
                default_res_model: this.res_model,
            }
        }).then(function (recordID) {
            self.handle= recordID;
            var record = self.model.get(self.handle);
            self._makeFields(record);
        });
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Activity composer not used standard renderer.
     * this method return field definition required to construct model
     * @private
     * @returns {Object} collection of fields with it definition.
     */
    _getFileds: function () {
        return {
            activity_type_id: {
                relation: 'mail.activity.type',
                type: 'many2one',
                name: 'activity_type_id',
                onChange: "1",
                required: true,
            },
            user_id: {
                relation: 'res.users',
                type: 'many2one',
                name: 'user_id',
                required: true,
            },
            date_deadline: {
                type: 'date',
                name: 'date_deadline',
                required: true,
            },
            summary: {
                type: 'char',
                name: 'summary',
            },
            note: {
                type: 'text',
                name: 'note',
            },
            res_id: {
                type: 'integer',
                name: 'res_id'
            },
            res_model_id: {
                relation: 'ir.model',
                type:  'many2one',
                name: 'res_model_id'
            },
            res_model: {
                type:  'char',
                name: 'res_model'
            }
        };
    },
    /**
     * @private
     */
    _makeFields : function (record) {
        this.fields.activity_type_id = this._createInstance(relational_fields.FieldMany2One, record, 'activity_type_id');
        this._registerWidget(this.handle, 'activity_type_id', this.fields.activity_type_id);
        this.fields.user_id = this._createInstance(relational_fields.FieldMany2One, record, 'user_id');
        this._registerWidget(this.handle, 'user_id', this.fields.user_id);
        this.fields.date_deadline = this._createInstance(basic_fields.FieldDate, record, 'date_deadline');
        this._registerWidget(this.handle, 'date_deadline', this.fields.date_deadline);
        this.fields.summary = this._createInstance(basic_fields.FieldChar, record, 'summary');
        this._registerWidget(this.handle, 'summary', this.fields.summary);
        this.fields.note = this._createInstance(basic_fields.FieldText, record, 'note');
        this._registerWidget(this.handle, 'note', this.fields.note);
    },
    /**
     * @private
     */
    _createInstance: function (klass, record, name){
        var FieldClass = klass.extend(_.extend(klass.prototype.events, {
            // Abstract field handle keydown event and pass it to controller as OdooEvent and prevent default
            // behavior. so override keydown and get back default behavior
            'keydown': function () {}
        }));
        return new FieldClass(this, name, record, {mode: 'edit'});
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.fields.activity_type_id.appendTo(this.$('.activity_type_id .o_td_field'))
            .then(addRequiredStyle(self.fields.activity_type_id));
        this.fields.user_id.appendTo(this.$('.user_id .o_td_field'))
            .then(addRequiredStyle(self.fields.user_id));
        this.fields.date_deadline.appendTo(this.$('.date_deadline .o_td_field'))
            .then(addRequiredStyle(self.fields.date_deadline));
        this.fields.summary.appendTo(this.$('.summary .o_td_field'));
        this.fields.note.appendTo(this.$('.note .o_td_field'))
            .then(function (){ self.fields.note.$el.addClass('form-control o_activity_textarea');});

        function addRequiredStyle(widget) {
            widget.$el.addClass('o_required_modifier');
        }
    },
    /**
     * Get the list of required field which are not set.
     *
     * @public
     * @returns {Array} list of invalid fields
     */
    getInvalidFields : function () {
        var invalidFields = _.filter(this.fields, function (field) {
            if (field.attrs.required) {
                return !(field.isValid() && field.isSet());
            }
            return false;
        });
        return invalidFields;
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onScheduleActivity: function () {
        var self = this;
        var invalidFields = this.getInvalidFields();
        if (invalidFields.length) {
            this.do_warn(_t("Please fill out all required fields"));
        } else {
            this.model.save(this.handle).then(function () {
                self.trigger_up('reload_mail_fields', {activity: true, thread: true});
            });
        }
    },

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onEditActivity: function (ev) {
        var record = this.model.get(this.handle, {raw: true});
        var options = {
            context : {}
        };
        _.each(record.data, function (value, field){
            options.context['default_' + field] = value;
        });
        this.trigger_up('edit_mail_activity', {target:ev, options:options});
    }
});

return ActivityComposer;
});