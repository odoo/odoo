odoo.define('web.Sidebar', function (require) {
"use strict";

var Context = require('web.Context');
var core = require('web.core');
var pyUtils = require('web.py_utils');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var Sidebar = Widget.extend({
    events: {
        "click a.dropdown-item": "_onDropdownClicked"
    },
    /**
     * @override
     *
     * @param {Object} options
     * @param {Object} options.items
     * @param {Object} options.sections
     * @param {Object} options.env
     * @param {Object} options.actions
     *
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = _.defaults(options || {}, {
            'editable': true
        });
        this.env = options.env;
        this.sections = options.sections || [
            {name: 'print', label: _t('Print')},
            {name: 'other', label: _t('Action')},
        ];
        this.items = options.items || {
            print: [],
            other: [],
        };
        if (options.actions) {
            this._addToolbarActions(options.actions);
        }
    },
    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        this.$el.addClass('btn-group');
        this._redraw();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Update the env for the sidebar then rerender it.
     *
     * @param  {Object} env
     */
    updateEnv: function (env) {
        this.env = env;
        this._redraw();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * For each item added to the section:
     *
     * ``label``
     *     will be used as the item's name in the sidebar, can be html
     *
     * ``action``
     *     descriptor for the action which will be executed, ``action`` and
     *     ``callback`` should be exclusive
     *
     * ``callback``
     *     function to call when the item is clicked in the sidebar, called
     *     with the item descriptor as its first argument (so information
     *     can be stored as additional keys on the object passed to
     *     ``_addItems``)
     *
     * ``classname`` (optional)
     *     ``@class`` set on the sidebar serialization of the item
     *
     * ``title`` (optional)
     *     will be set as the item's ``@title`` (tooltip)
     *
     * @private
     * @param {String} sectionCode
     * @param {Array<{label, action | callback[, classname][, title]}>} items
     */
    _addItems: function (sectionCode, items) {
        if (items) {
            this.items[sectionCode].unshift.apply(this.items[sectionCode], items);
        }
    },
    /**
     * Method that will add the custom actions to the toolbar
     *
     * @private
     * @param {Object} toolbarActions
     */
    _addToolbarActions: function (toolbarActions) {
        var self = this;
        _.each(['print','action','relate'], function (type) {
            if (type in toolbarActions) {
                var actions = toolbarActions[type];
                if (actions && actions.length) {
                    var items = _.map(actions, function (action) {
                        return {
                            label: action.name,
                            action: action,
                        };
                    });
                    self._addItems(type === 'print' ? 'print' : 'other', items);
                }
            }
        });
        if ('other' in toolbarActions) {
            this._addItems('other', toolbarActions.other);
        }
    },
    /**
     * Performs the action for the item clicked after getting the data
     * necessary with a trigger up
     *
     * @private
     * @param  {Object} item
     */
    _onItemActionClicked: function (item) {
        var self = this;
        this.trigger_up('sidebar_data_asked', {
            callback: function (env) {
                self.env = env;
                var activeIdsContext = {
                    active_id: env.activeIds[0],
                    active_ids: env.activeIds,
                    active_model: env.model,
                };
                if (env.domain) {
                    activeIdsContext.active_domain = env.domain;
                }

                var context = pyUtils.eval('context', new Context(env.context, activeIdsContext));
                self._rpc({
                    route: '/web/action/load',
                    params: {
                        action_id: item.action.id,
                        context: context,
                    },
                }).then(function (result) {
                    result.context = new Context(
                        result.context || {}, activeIdsContext)
                            .set_eval_context(context);
                    result.flags = result.flags || {};
                    result.flags.new_window = true;
                    self.do_action(result, {
                        on_close: function () {
                            self.trigger_up('reload');
                        },
                    });
                });
            }
        });
    },
    /**
     * Method that renders the sidebar when there is a data update
     *
     * @private
     */
    _redraw: function () {
        this.$el.html(QWeb.render('Sidebar', {widget: this}));

        // Hides Sidebar sections when item list is empty
        _.each(this.$('.o_dropdown'), function (el) {
            var $dropdown = $(el);
            if (!$dropdown.find('.dropdown-item').length) {
                $dropdown.hide();
            }
        });
        this.$("[title]").tooltip({
            delay: { show: 500, hide: 0}
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Method triggered when the user clicks on a toolbar dropdown
     *
     * @private
     * @param  {MouseEvent} event
     */
    _onDropdownClicked: function (event) {
        var section = $(event.currentTarget).data('section');
        var index = $(event.currentTarget).data('index');
        var item = this.items[section][index];
        if (item.callback) {
            item.callback.apply(this, [item]);
        } else if (item.action) {
            this._onItemActionClicked(item);
        } else if (item.url) {
            return true;
        }
        event.preventDefault();
    },
});

return Sidebar;

});
