odoo.define("mail.ActivityCell", function (require) {
    "use strict";

    require("mail.Activity");
    const field_registry = require('web.field_registry');

    const KanbanActivity = field_registry.get('kanban_activity');

    const ActivityCell = KanbanActivity.extend({
        /**
         * @override
         * @private
         */
        _render() {
            // replace clock by closest deadline
            const $date = $('<div class="o_closest_deadline">');
            const date = moment(this.record.data.closest_deadline).toDate();
            // To remove year only if current year
            if (moment().year() === moment(date).year()) {
                $date.text(date.toLocaleDateString(moment().locale(), {
                    day: 'numeric', month: 'short'
                }));
            } else {
                $date.text(moment(date).format('ll'));
            }
            this.$('a').html($date);
            if (this.record.data.activity_ids.res_ids.length > 1) {
                this.$('a').append($('<span>', {
                    class: 'badge badge-light badge-pill border-0 ' + this.record.data.activity_state,
                    text: this.record.data.activity_ids.res_ids.length,
                }));
            }
            if (this.$el.hasClass('show')) {
                // note: this part of the rendering might be asynchronous
                this._renderDropdown();
            }
        }
    });

    return ActivityCell;

});
