odoo.define('mail.ActivityModel', function (require) {
'use strict';

const BasicModel = require('web.BasicModel');
const session = require('web.session');

const ActivityModel = BasicModel.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * Add the following (activity specific) keys when performing a `get` on the
     * main list datapoint:
     * - activity_types
     * - activity_res_ids
     * - grouped_activities
     *
     * @override
     */
    get: function () {
        var result = this._super.apply(this, arguments);
        if (result && result.model === this.modelName && result.type === 'list') {
            _.extend(result, this.additionalData, {getKanbanActivityData: this.getKanbanActivityData});
        }
        return result;
    },
    /**
     * @param {Object} activityGroup
     * @param {integer} resId
     * @returns {Object}
     */
    getKanbanActivityData(activityGroup, resId) {
        return {
            data: {
                activity_ids: {
                    model: 'mail.activity',
                    res_ids: activityGroup.ids,
                },
                activity_state: activityGroup.state,
                closest_deadline: activityGroup.o_closest_deadline,
            },
            fields: {
                activity_ids: {},
                activity_state: {
                    selection: [
                        ['overdue', "Overdue"],
                        ['today', "Today"],
                        ['planned', "Planned"],
                    ],
                },
            },
            fieldsInfo: {},
            model: this.model,
            type: 'record',
            res_id: resId,
            getContext: function () {
                return {};
            },
        };
    },
    /**
     * @override
     * @param {Array[]} params.domain
     */
    load: function (params) {
        this.originalDomain = _.extend([], params.domain);
        params.domain.push(['activity_ids', '!=', false]);
        this.domain = params.domain;
        this.modelName = params.modelName;
        params.groupedBy = [];
        var def = this._super.apply(this, arguments);
        return Promise.all([def, this._fetchData()]).then(function (result) {
            return result[0];
        });
    },
    /**
     * @override
     * @param {Array[]} [params.domain]
     */
    reload: function (handle, params) {
        if (params && 'domain' in params) {
            this.originalDomain = _.extend([], params.domain);
            params.domain.push(['activity_ids', '!=', false]);
            this.domain = params.domain;
        }
        if (params && 'groupBy' in params) {
            params.groupBy = [];
        }
        var def = this._super.apply(this, arguments);
        return Promise.all([def, this._fetchData()]).then(function (result) {
            return result[0];
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetch activity data.
     *
     * @private
     * @returns {Promise}
     */
    _fetchData: function () {
        var self = this;
        return this._rpc({
            model: "mail.activity",
            method: 'get_activity_data',
            kwargs: {
                res_model: this.modelName,
                domain: this.domain,
                context: session.user_context,
            }
        }).then(function (result) {
            self.additionalData = result;
        });
    },
});

return ActivityModel;

});
