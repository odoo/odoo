/** @odoo-module **/

import KanbanRecord from 'web.KanbanRecord';

var ActivityRecord = KanbanRecord.extend({
    custom_events: Object.assign({}, KanbanRecord.prototype.custom_events, {
        open_record: (ev) => {
            ev.data.mode = "edit";
        },
    }),
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
            luxon,
        };
    },
});

export default ActivityRecord;
