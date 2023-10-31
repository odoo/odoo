odoo.define('web.GraphController', function (require) {
"use strict";

/*---------------------------------------------------------
 * Odoo Graph view
 *---------------------------------------------------------*/

const AbstractController = require('web.AbstractController');
const { ComponentWrapper } = require('web.OwlCompatibility');
const DropdownMenu = require('web.DropdownMenu');
const { DEFAULT_INTERVAL, INTERVAL_OPTIONS } = require('web.searchUtils');
const { qweb } = require('web.core');
const { _t } = require('web.core');

class CarretDropdownMenu extends DropdownMenu {
    /**
     * @override
     */
    get displayCaret() {
        return true;
    }
}

var GraphController = AbstractController.extend({
    custom_events: _.extend({}, AbstractController.prototype.custom_events, {
        item_selected: '_onItemSelected',
        open_view: '_onOpenView',
    }),

    /**
     * @override
     * @param {Widget} parent
     * @param {GraphModel} model
     * @param {GraphRenderer} renderer
     * @param {Object} params
     * @param {string[]} params.measures
     * @param {boolean} params.isEmbedded
     * @param {string[]} params.groupableFields,
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.measures = params.measures;
        // this parameter condition the appearance of a 'Group By'
        // button in the control panel owned by the graph view.
        this.isEmbedded = params.isEmbedded;
        this.withButtons = params.withButtons;
        // views to use in the action triggered when the graph is clicked
        this.views = params.views;
        this.title = params.title;

        // this parameter determines what is the list of fields
        // that may be used within the groupby menu available when
        // the view is embedded
        this.groupableFields = params.groupableFields;
        this.buttonDropdownPromises = [];
    },
    /**
     * @todo check if this can be removed (mostly duplicate with
     * AbstractController method)
     */
    destroy: function () {
        if (this.$buttons) {
            // remove jquery's tooltip() handlers
            this.$buttons.find('button').off().tooltip('dispose');
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the current mode, measure and groupbys, so we can restore the
     * view when we save the current state in the search view, or when we add it
     * to the dashboard.
     *
     * @override
     * @returns {Object}
     */
    getOwnedQueryParams: function () {
        var state = this.model.get();
        return {
            context: {
                graph_measure: state.measure,
                graph_mode: state.mode,
                graph_groupbys: state.groupBy,
            }
        };
    },
    /**
     * @override
     */
    reload: async function () {
        const promises = [this._super(...arguments)];
        if (this.withButtons) {
            const state = this.model.get();
            this.measures.forEach(m => m.isActive = m.fieldName === state.measure);
            promises.push(this.measureMenu.update({ items: this.measures }));
        }
        return Promise.all(promises);
    },
    /**
     * Render the buttons according to the GraphView.buttons and
     * add listeners on it.
     * Set this.$buttons with the produced jQuery element
     *
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should
     * be inserted $node may be undefined, in which case the GraphView does
     * nothing
     */
    renderButtons: function ($node) {
        this.$buttons = $(qweb.render('GraphView.buttons'));
        this.$buttons.find('button').tooltip();
        this.$buttons.click(ev => this._onButtonClick(ev));

        if (this.withButtons) {
            const state = this.model.get();
            const fragment = document.createDocumentFragment();
            // Instantiate and append MeasureMenu
            this.measures.forEach(m => m.isActive = m.fieldName === state.measure);
            this.measureMenu = new ComponentWrapper(this, CarretDropdownMenu, {
                title: _t("Measures"),
                items: this.measures,
            });
            this.buttonDropdownPromises = [this.measureMenu.mount(fragment)];
            if (this.isEmbedded) {
                // Instantiate and append GroupBy menu
                this.groupByMenu = new ComponentWrapper(this, CarretDropdownMenu, {
                    title: _t("Group By"),
                    icon: 'fa fa-bars',
                    items: this._getGroupBys(state.groupBy),
                });
                this.buttonDropdownPromises.push(this.groupByMenu.mount(fragment));
            }
            if ($node) {
                this.$buttons.appendTo($node);
            }
        }
    },
    /**
     * Makes sure that the buttons in the control panel matches the current
     * state (so, correct active buttons and stuff like that).
     *
     * @override
     */
    updateButtons: function () {
        if (!this.$buttons) {
            return;
        }
        var state = this.model.get();
        this.$buttons.find('.o_graph_button').removeClass('active');
        this.$buttons
            .find('.o_graph_button[data-mode="' + state.mode + '"]')
            .addClass('active');
        this.$buttons
            .find('.o_graph_button[data-mode="stack"]')
            .data('stacked', state.stacked)
            .toggleClass('active', state.stacked)
            .toggleClass('o_hidden', state.mode !== 'bar');
        this.$buttons
            .find('.o_graph_button[data-order]')
            .toggleClass('o_hidden', state.mode === 'pie' || !!Object.keys(state.timeRanges).length)
            .filter('.o_graph_button[data-order="' + state.orderBy + '"]')
            .toggleClass('active', !!state.orderBy);

        if (this.withButtons) {
            return this._attachDropdownComponents();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Attaches the different dropdown components to the buttons container.
     *
     * @returns {Promise}
     */
    async _attachDropdownComponents() {
        await Promise.all(this.buttonDropdownPromises);
        if (this.isDestroyed()) {
            return;
        }
        const actionsContainer = this.$buttons[0];
        // Attach "measures" button
        actionsContainer.appendChild(this.measureMenu.el);
        this.measureMenu.el.classList.add('o_graph_measures_list');
        if (this.isEmbedded) {
            // Attach "groupby" button
            actionsContainer.appendChild(this.groupByMenu.el);
            this.groupByMenu.el.classList.add('o_group_by_menu');
        }
        // Update button classes accordingly to the current mode
        const buttons = actionsContainer.querySelectorAll('.dropdown-toggle');
        for (const button of buttons) {
            button.classList.remove('btn-secondary');
            if (this.isEmbedded) {
                button.classList.add('btn-outline-secondary');
            } else {
                button.classList.add('btn-primary');
                button.tabIndex = 0;
            }
        }
    },

    /**
     * Returns the items used by the Group By menu in embedded mode.
     *
     * @private
     * @param {string[]} activeGroupBys
     * @returns {Object[]}
     */
    _getGroupBys(activeGroupBys) {
        const normalizedGroupBys = this._normalizeActiveGroupBys(activeGroupBys);
        const groupBys = Object.keys(this.groupableFields).map(fieldName => {
            const field = this.groupableFields[fieldName];
            const groupByActivity = normalizedGroupBys.filter(gb => gb.fieldName === fieldName);
            const groupBy = {
                id: fieldName,
                isActive: Boolean(groupByActivity.length),
                description: field.string,
                itemType: 'groupBy',
            };
            if (['date', 'datetime'].includes(field.type)) {
                groupBy.hasOptions = true;
                const activeOptionIds = groupByActivity.map(gb => gb.interval);
                groupBy.options = Object.values(INTERVAL_OPTIONS).map(o => {
                    return Object.assign({}, o, { isActive: activeOptionIds.includes(o.id) });
                });
            }
            return groupBy;
        }).sort((gb1, gb2) => {
            return gb1.description.localeCompare(gb2.description);
        });
        return groupBys;
    },

    /**
     * This method puts the active groupBys in a convenient form.
     *
     * @private
     * @param {string[]} activeGroupBys
     * @returns {Object[]} normalizedGroupBys
     */
    _normalizeActiveGroupBys(activeGroupBys) {
        return activeGroupBys.map(groupBy => {
            const fieldName = groupBy.split(':')[0];
            const field = this.groupableFields[fieldName];
            const normalizedGroupBy = { fieldName };
            if (['date', 'datetime'].includes(field.type)) {
                normalizedGroupBy.interval = groupBy.split(':')[1] || DEFAULT_INTERVAL;
            }
            return normalizedGroupBy;
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Do what need to be done when a button from the control panel is clicked.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onButtonClick: function (ev) {
        var $target = $(ev.target);
        if ($target.hasClass('o_graph_button')) {
            if (_.contains(['bar','line', 'pie'], $target.data('mode'))) {
                this.update({ mode: $target.data('mode') });
            } else if ($target.data('mode') === 'stack') {
                this.update({ stacked: !$target.data('stacked') });
            } else if (['asc', 'desc'].includes($target.data('order'))) {
                const order = $target.data('order');
                const state = this.model.get();
                this.update({ orderBy: state.orderBy === order ? false : order });
            }
        }
    },

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onItemSelected(ev) {
        const item = ev.data.item;
        if (this.isEmbedded && item.itemType === 'groupBy') {
            const fieldName = item.id;
            const optionId = ev.data.option && ev.data.option.id;
            const activeGroupBys = this.model.get().groupBy;
            if (optionId) {
                const normalizedGroupBys = this._normalizeActiveGroupBys(activeGroupBys);
                const index = normalizedGroupBys.findIndex(ngb =>
                    ngb.fieldName === fieldName && ngb.interval === optionId);
                if (index === -1) {
                    activeGroupBys.push(fieldName + ':' + optionId);
                } else {
                    activeGroupBys.splice(index, 1);
                }
            } else {
                const groupByFieldNames = activeGroupBys.map(gb => gb.split(':')[0]);
                const indexOfGroupby = groupByFieldNames.indexOf(fieldName);
                if (indexOfGroupby === -1) {
                    activeGroupBys.push(fieldName);
                } else {
                    activeGroupBys.splice(indexOfGroupby, 1);
                }
            }
            this.update({ groupBy: activeGroupBys });
            this.groupByMenu.update({
                items: this._getGroupBys(activeGroupBys),
            });
        } else if (item.itemType === 'measure') {
            this.update({ measure: item.fieldName });
            this.measures.forEach(m => m.isActive = m.fieldName === item.fieldName);
            this.measureMenu.update({ items: this.measures });
        }
    },

    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Array[]} ev.data.domain
     */
    _onOpenView(ev) {
        ev.stopPropagation();
        const state = this.model.get();
        const context = Object.assign({}, state.context);
        Object.keys(context).forEach(x => {
            if (x === 'group_by' || x.startsWith('search_default_')) {
                delete context[x];
            }
        });
        this.do_action({
            context: context,
            domain: ev.data.domain,
            name: this.title,
            res_model: this.modelName,
            target: 'current',
            type: 'ir.actions.act_window',
            view_mode: 'list',
            views: this.views,
        });
    },
});

return GraphController;

});
