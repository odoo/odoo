odoo.define('web.KanbanRendererMobile', function (require) {
"use strict";

/**
 * The purpose of this file is to improve the UX of grouped kanban views in
 * mobile. It includes the KanbanRenderer (in mobile only) to only display one
 * column full width, and enables the swipe to browse to the other columns.
 * Moreover, records in columns are lazy-loaded.
 */

var config = require('web.config');
var core = require('web.core');
var KanbanRenderer = require('web.KanbanRenderer');

var _t = core._t;
var qweb = core.qweb;

if (!config.device.isMobile) {
    return;
}

KanbanRenderer.include({
    events: _.extend({}, KanbanRenderer.prototype.events, {
        'click .o_kanban_mobile_tab': '_onMobileTabClicked',
    }),
    ANIMATE: true, // allows to disable animations for the tests
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.activeColumnIndex = 0; // index of the currently displayed column
        this._scrollPosition = null;
    },
    /**
     * As this renderer defines its own scrolling area (the column in grouped
     * mode), we override this hook to restore the scroll position like it was
     * when the renderer has been last detached.
     *
     * @override
     */
    on_attach_callback: function () {
        if (this._scrollPosition && this.state.groupedBy.length && this.widgets.length) {
            var $column = this.widgets[this.activeColumnIndex].$el;
            $column.scrollLeft(this._scrollPosition.left);
            $column.scrollTop(this._scrollPosition.top);
        }
        this._computeTabPosition();
        this._super.apply(this, arguments);
    },
    /**
     * As this renderer defines its own scrolling area (the column in grouped
     * mode), we override this hook to store the scroll position, so that we can
     * restore it if the renderer is re-attached to the DOM later.
     *
     * @override
     */
    on_detach_callback: function () {
        if (this.state.groupedBy.length && this.widgets.length) {
            var $column = this.widgets[this.activeColumnIndex].$el;
            this._scrollPosition = {
                left: $column.scrollLeft(),
                top: $column.scrollTop(),
            };
        } else {
            this._scrollPosition = null;
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Displays the quick create record in the active column
     *
     * @returns {Promise}
     */
    addQuickCreate: function () {
        return this.widgets[this.activeColumnIndex].addQuickCreate();
    },
    /**
     * Overrides to restore the left property and the scrollTop on the updated
     * column, and to enable the swipe handlers
     *
     * @override
     */
    updateColumn: function (localID) {
        var self = this;
        var index = _.findIndex(this.widgets, {db_id: localID});
        var $column = this.widgets[index].$el;
        var left = $column.css('left');
        var right = $column.css('right');
        var scrollTop = $column.scrollTop();
        return this._super.apply(this, arguments).then(function () {
            $column = self.widgets[index].$el;
            if (_t.database.parameters.direction === 'rtl') {
                $column.css({right: right});
            } else {
                $column.css({left: left});
            }
            $column.scrollTop(scrollTop); // required when clicking on 'Load More'
            self._enableSwipe();
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Update the columns positions
     *
     * @private
     * @param {boolean} [animate=false] set to true to animate
     */
    _computeColumnPosition: function (animate) {
        if (this.widgets.length) {
            var self = this;
            var moveToIndex = this.activeColumnIndex;
            var updateFunc = animate ? 'animate' : 'css';
            var rtl = _t.database.parameters.direction === 'rtl';
            _.each(this.widgets, function (column, index) {
                var columnID = column.id || column.db_id;
                var $column = self.$('.o_kanban_group[data-id="' + columnID + '"]');
                if (index === moveToIndex - 1) {
                    if (rtl) {
                        $column[updateFunc]({right: '-100%'});
                    } else {
                        $column[updateFunc]({left: '-100%'});
                    }
                } else if (index === moveToIndex + 1) {
                    if (rtl) {
                        $column[updateFunc]({right: '100%'});
                    } else {
                        $column[updateFunc]({left: '100%'});
                    }
                } else if (index === moveToIndex) {
                    if (rtl) {
                        $column[updateFunc]({right: '0%'});
                    } else {
                        $column[updateFunc]({left: '0%'});
                    }
                } else if (index < moveToIndex) {
                    if (rtl) {
                        $column.css({right: '-100%'});
                    } else {
                        $column.css({left: '-100%'});
                    }
                } else if (index > moveToIndex) {
                    if (rtl) {
                        $column.css({right: '100%'});
                    } else {
                        $column.css({left: '100%'});
                    }
                }
            });
        }
    },

    /**
     * Define the o_current class to the current selected kanban (column & tab)
     *
     * @private
     */
    _computeCurrentColumn: function () {
        if (this.widgets.length) {
            var column = this.widgets[this.activeColumnIndex];
            if (!column) {
                return;
            }
            var columnID = column.id || column.db_id;
            this.$('.o_kanban_mobile_tab.o_current, .o_kanban_group.o_current')
                .removeClass('o_current');
            this.$('.o_kanban_group[data-id="' + columnID + '"], ' +
                   '.o_kanban_mobile_tab[data-id="' + columnID + '"]')
                .addClass('o_current');
        }
    },

    /**
     * Update the tabs positions
     *
     * @private
     */
    _computeTabPosition: function () {
        this._computeTabJustification();
        this._computeTabScrollPosition();
    },

    /**
     * Update the tabs positions
     *
     * @private
     */
    _computeTabScrollPosition: function () {
        if (this.widgets.length) {
            var lastItemIndex = this.widgets.length - 1;
            var moveToIndex = this.activeColumnIndex;
            var scrollToLeft = 0;
            for (var i = 0; i < moveToIndex; i++) {
                var columnWidth = this._getTabWidth(this.widgets[i]);
                // apply
                if (moveToIndex !== lastItemIndex && i === moveToIndex - 1) {
                    var partialWidth = 0.75;
                    scrollToLeft += columnWidth * partialWidth;
                } else {
                    scrollToLeft += columnWidth;
                }
            }
            // Apply the scroll x on the tabs
            // XXX in case of RTL, should we use scrollRight?
            this.$('.o_kanban_mobile_tabs').scrollLeft(scrollToLeft);
        }
    },

    /**
     * Compute the justify content of the kanban tab headers
     *
     * @private
     */
    _computeTabJustification: function () {
        if (this.widgets.length) {
            var self = this;
            // Use to compute the sum of the width of all tab
            var widthChilds = this.widgets.reduce(function (total, column) {
                return total + self._getTabWidth(column);
            }, 0);
            // Apply a space around between child if the parent length is higher then the sum of the child width
            var $tabs = this.$('.o_kanban_mobile_tabs');
            $tabs.toggleClass('justify-content-around', $tabs.outerWidth() >= widthChilds);
        }
    },

    /**
     * Enables swipe event on the current column
     *
     * @private
     */
    _enableSwipe: function () {
        var self = this;
        var step = _t.database.parameters.direction === 'rtl' ? -1 : 1;
        this.$el.swipe({
            excludedElements: ".o_kanban_mobile_tabs",
            swipeLeft: function () {
                var moveToIndex = self.activeColumnIndex + step;
                if (moveToIndex < self.widgets.length) {
                    self._moveToGroup(moveToIndex, self.ANIMATE);
                }
            },
            swipeRight: function () {
                var moveToIndex = self.activeColumnIndex - step;
                if (moveToIndex > -1) {
                    self._moveToGroup(moveToIndex, self.ANIMATE);
                }
            }
        });
    },

    /**
     * Retrieve the outerWidth of a given widget column
     *
     * @param {KanbanColumn} column
     * @returns {integer} outerWidth of the found column
     * @private
     */
    _getTabWidth : function (column) {
        var columnID = column.id || column.db_id;
        return this.$('.o_kanban_mobile_tab[data-id="' + columnID + '"]').outerWidth();
    },

    /**
     * Update the kanban layout
     *
     * @private
     * @param {boolean} [animate=false] set to true to animate
     */
    _layoutUpdate : function (animate) {
        this._computeCurrentColumn();
        this._computeTabPosition();
        this._computeColumnPosition(animate);
    },

    /**
     * Moves to the given kanban column
     *
     * @private
     * @param {integer} moveToIndex index of the column to move to
     * @param {boolean} [animate=false] set to true to animate
     * @returns {Promise} resolved when the new current group has been loaded
     *   and displayed
     */
    _moveToGroup: function (moveToIndex, animate) {
        var self = this;
        if (moveToIndex < 0 || moveToIndex >= this.widgets.length) {
            this._layoutUpdate(animate);
            return Promise.resolve();
        }
        this.activeColumnIndex = moveToIndex;
        var column = this.widgets[this.activeColumnIndex];
        return new Promise(function (resolve) {
            self.trigger_up('kanban_load_records', {
                columnID: column.db_id,
                onSuccess: function () {
                    self._layoutUpdate(animate);
                    resolve();
                },
            });
        });
    },

    /**
     * @override
     * @private
     */
    _renderGrouped: function (fragment) {
        var self = this;
        this._super.apply(this, arguments);
        this.defs.push(Promise.all(this.defs).then(function () {
            var data = [];
            _.each(self.state.data, function (group) {
                if (!group.value) {
                    group = _.extend({}, group, {value: _t('Undefined')});
                    data.unshift(group);
                } else {
                    data.push(group);
                }
            });

            $(qweb.render('KanbanView.MobileTabs', {
                data: data,
            })).prependTo(fragment);
        }));
    },

    /**
     * @override
     * @private
     */
    _renderView: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            if (self.state.groupedBy.length) {
                // force first column for kanban view, because the groupedBy can be changed
                return self._moveToGroup(0);
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onMobileTabClicked: function (event) {
        this._moveToGroup($(event.currentTarget).index(), true);
    },
});

});
