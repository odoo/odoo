/** @odoo-module **/

/**
 * This Kanban Model make sure we display a rainbowman
 * message when a lead is won after we moved it in the
 * correct column and when it's grouped by stage_id (default).
 * Apart from that, in the KanbanColumnProgressBar, we add
 * support for showing sum of the expected MRR (after the regular
 * sum field) if the logged user has the enough rights.
 */

import KanbanColumn from 'web.KanbanColumn';
import KanbanColumnProgressBar from 'web.KanbanColumnProgressBar';
import KanbanModel from 'web.KanbanModel';
import KanbanRenderer from 'web.KanbanRenderer';
import KanbanView from 'web.KanbanView';
import utils from 'web.utils';
import viewRegistry from 'web.view_registry';

const CrmKanbanColumnProgressBar = KanbanColumnProgressBar.extend({

    /**
     * @constructor
     * @override
     */
    init(parent, options, columnState) {
        this._super.apply(this, arguments);
        this.recurringRevenueSumField = columnState.progressBarValues.recurring_revenue_sum_field;
        // Check whether the given MRR sum field is valid or not
        this.isRecurringRevenueSumFieldValid = Object.keys(columnState.fields).includes(columnState.progressBarValues.recurring_revenue_sum_field);
        this.recurringRevenueSumFieldLabel = this.isRecurringRevenueSumFieldValid ? columnState.fields[this.recurringRevenueSumField].string : false;
        // Previous progressBar state
        const state = options.progressBarStates[this.columnID];
        if (state) {
            this.totalRecurringRevenue = state.totalRecurringRevenue;
        }
    },

    /**
     * @override
     */
    willStart() {
        const userHasGroup = this.getSession().user_has_group('crm.group_use_recurring_revenues')
            .then((useRecurringRevenues) => {
                // only show MRR related info if 'Recurring Revenues' is enabled, and provided MRR sum field is valid
                this.showRecurringRevenue = useRecurringRevenues && this.isRecurringRevenueSumFieldValid;
            });
        return Promise.all([this._super(...arguments), userHasGroup]);
    },

    /**
     * @override
     */
    start() {
        const def = this._super.apply(this, arguments);

        if (!this.showRecurringRevenue) {
            return def;
        }

        this.$mrrCounter = this.$counter.filter('.o_crm_kanban_mrr_counter_side');
        this.$recurringRevenueNumber = this.$mrrCounter.find('.o_crm_kanban_mrr_sum');
        // the MRR counter has it's own width, and so if we put the '+' symbol outside it,
        // '+' will be more close to the actual sum field and far from MRR, especially if
        //  MRR has single digit value and text is aligned right, so we put it within MRR.
        let $plus = $('<strong/>', {
            text: '+',
        });
        this.$('.o_kanban_counter_progress').addClass('o_crm_kanban_counter_progress_mrr w-50');
        this.$mrrCounter.prepend($plus);
        return def;
    },

    /**
     * @override
     */
    computeCounters() {
        this._super.apply(this, arguments);
        if (this.showRecurringRevenue) {
            this.prevTotalRecurringRevenue = this.totalRecurringRevenue;
            this.totalRecurringRevenue = this.columnState.aggregateValues[this.recurringRevenueSumField] || 0;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _render() {
        const self = this;
        const res = this._super.apply(this, arguments);

        if (!this.showRecurringRevenue) {
            return res;
        }

        const startMRR = this.prevTotalRecurringRevenue;
        let endMRR = this.totalRecurringRevenue;

        if (this.activeFilter.value) {
            endMRR = 0;
            this.columnState.data.forEach((record) => {
                if (this.activeFilter.value === record.data[this.fieldName] ||
                    (this.activeFilter.value === '__false' && !record.data[this.fieldName])) {
                    endMRR += parseFloat(record.data[this.recurringRevenueSumField]);
                }
            });
        }

        this.prevTotalRecurringRevenue = endMRR;

        if (startMRR !== undefined && (endMRR > startMRR || this.activeFilter.value) && this.ANIMATE) {
            $({currentValue: startMRR}).animate({currentValue: endMRR}, {
                duration: 1000,
                start: function () {
                    // always use 'o_kanban_grow' class due to limited length
                    self.$counter.removeClass('o_kanban_grow_huge');
                    self.$counter.addClass('o_kanban_grow');
                    self.$mrrCounter.addClass('o_kanban_grow');
                },
                step: function () {
                    self.$recurringRevenueNumber.text(utils.human_number(this.currentValue));
                },
                complete: function () {
                    self.$recurringRevenueNumber.text(utils.human_number(this.currentValue));
                    self.$counter.removeClass('o_kanban_grow');
                    self.$mrrCounter.removeClass('o_kanban_grow');
                },
            });
        } else {
            this.$recurringRevenueNumber.text(utils.human_number(endMRR));
        }
        return res;
    },

    /**
     * @private
     * @override
     */
    _getNotifyStateValues: function() {
        const res = this._super.apply(this, arguments);
        if (this.showRecurringRevenue) {
            res.totalRecurringRevenue = this.totalRecurringRevenue;
        }
        return res;
    },
});

const CrmKanbanColumn = KanbanColumn.extend({
    /**
     * @private
     * @override
     */
    _getKanbanColumnProgressBar: function () {
        return new CrmKanbanColumnProgressBar(this, this.barOptions, this.data);
    },
});

var CrmKanbanModel = KanbanModel.extend({
    /**
     * Check if the kanban view is grouped by "stage_id" before checking if the lead is won
     * and displaying a possible rainbowman message.
     * @override
     */
    moveRecord: async function (recordID, groupID, parentID) {
        var result = await this._super(...arguments);
        if (this.localData[parentID].groupedBy[0] === this.defaultGroupedBy[0]) {
            const message = await this._rpc({
                model: 'crm.lead',
                method : 'get_rainbowman_message',
                args: [[parseInt(this.localData[recordID].res_id)]],
            });
            if (message) {
                this.trigger_up('show_effect', {
                    message: message,
                    type: 'rainbow_man',
                });
            }
        }
        return result;
    },
});

const CrmKanbanRenderer = KanbanRenderer.extend({
    config: Object.assign({}, KanbanRenderer.prototype.config, {
        KanbanColumn: CrmKanbanColumn,
    }),
});

var CrmKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Model: CrmKanbanModel,
        Renderer: CrmKanbanRenderer,
    }),
});

viewRegistry.add('crm_kanban', CrmKanbanView);

export default {
    CrmKanbanColumn: CrmKanbanColumn,
    CrmKanbanColumnProgressBar: CrmKanbanColumnProgressBar,
    CrmKanbanModel: CrmKanbanModel,
    CrmKanbanRenderer: CrmKanbanRenderer,
    CrmKanbanView: CrmKanbanView
};