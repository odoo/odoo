odoo.define('mail.ActivityRecord', function (require) {
"use strict";

var KanbanRecord = require('web.KanbanRecord');

var ActivityRecord = KanbanRecord.extend({
    /**
     * @override
     */
    init: function (parent, state) {
        this._super.apply(this,arguments);

        this.fieldsInfo = state.fieldsInfo.activity;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        this.defs = [];
        this._replaceElement(this.qweb.render('activity-box', this.qweb_context));
        this.$el.on('click', this._onGlobalClick.bind(this));
        this.$el.addClass('o_activity_record');
        this._processFields();
        this._setupColor();
        return Promise.all(this.defs);
    },
    /**
     * @override
     * @private
     */
    _setFieldDisplay: function ($el, fieldName) {
        this._super.apply(this, arguments);

        // attribute muted
        if (this.fieldsInfo[fieldName].muted) {
            $el.addClass('text-muted');
        }
    },
    /**
     * @override
     * @private
     */
    _setState: function () {
        this._super.apply(this, arguments);

        // activity has a different qweb context
        this.qweb_context = {
            activity_image: this._getImageURL.bind(this),
            record: this.record,
            user_context: this.getSession().user_context,
            widget: this,
        };
    },
        /**
     * @private
     * @param {string} model the name of the model
     * @param {string} field the name of the field
     * @param {integer} id the id of the resource
     * @param {string} placeholder
     * @returns {string} the url of the image
     */
    _getImageURL: function (model, field, id, placeholder) {
        id = (_.isArray(id) ? id[0] : id) || null;
        var isCurrentRecord = this.modelName === model && this.recordData.id === id;
        var url;
        if (isCurrentRecord && this.record[field] && this.record[field].raw_value && !utils.is_bin_size(this.record[field].raw_value)) {
            // Use magic-word technique for detecting image type
            url = 'data:image/' + this.file_type_magic_word[this.record[field].raw_value[0]] + ';base64,' + this.record[field].raw_value;
        } else {
            var session = this.getSession();
            var params = {
                model: model,
                field: field,
                id: id
            };
            if (isCurrentRecord) {
                params.unique = this.record.__last_update && this.record.__last_update.value.replace(/[^0-9]/g, '');
            }
            url = params.unique ?
                session.url(`/web/avatar/${model}/${id}/${field}?unique=${params.unique}`) :
                session.url(`/web/avatar/${model}/${id}/${field}`)
        }
        return url;
    },
});
return ActivityRecord;
});
