odoo.define("web_responsive.KanbanRendererMobile", function (require) {
    "use strict";

    /**
     * The purpose of this file is to improve the UX of grouped kanban views in
     * mobile. It includes the KanbanRenderer (in mobile only) to only display one
     * column full width, and enables the swipe to browse to the other columns.
     * Moreover, records in columns are lazy-loaded.
     */

    var config = require("web.config");
    var core = require("web.core");
    var KanbanRenderer = require("web.KanbanRenderer");
    var KanbanView = require("web.KanbanView");
    var KanbanQuickCreate = require("web.kanban_column_quick_create");

    var _t = core._t;
    var qweb = core.qweb;

    if (!config.device.isMobile) {
        return;
    }

    KanbanQuickCreate.include({
        init() {
            this._super.apply(this, arguments);
            this.isMobile = true;
        },
        /**
         * KanbanRenderer will decide can we close quick create or not
         * @private
         * @override
         */
        _cancel: function () {
            this.trigger_up("close_quick_create");
        },
        /**
         * Clear input when showed
         * @override
         */
        toggleFold: function () {
            this._super.apply(this, arguments);
            if (!this.folded) {
                this.$input.val("");
            }
        },
    });

    KanbanView.include({
        init() {
            this._super.apply(this, arguments);
            this.jsLibs.push("/web/static/lib/jquery.touchSwipe/jquery.touchSwipe.js");
        },
    });

    KanbanRenderer.include({
        custom_events: _.extend({}, KanbanRenderer.prototype.custom_events || {}, {
            quick_create_column_created: "_onColumnAdded",
        }),
        events: _.extend({}, KanbanRenderer.prototype.events, {
            "click .o_kanban_mobile_tab": "_onMobileTabClicked",
            "click .o_kanban_mobile_add_column": "_onMobileQuickCreateClicked",
        }),
        ANIMATE: true, // Allows to disable animations for the tests
        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.activeColumnIndex = 0; // Index of the currently displayed column
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
            if (
                this._scrollPosition &&
                this.state.groupedBy.length &&
                this.widgets.length
            ) {
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

        // --------------------------------------------------------------------------
        // Public
        // --------------------------------------------------------------------------

        /**
         * Displays the quick create record in the active column
         * override to open quick create record in current active column
         *
         * @override
         * @returns {Promise}
         */
        addQuickCreate: function () {
            if (this._canCreateColumn() && !this.quickCreate.folded) {
                this._onMobileQuickCreateClicked();
            }
            return this.widgets[this.activeColumnIndex].addQuickCreate();
        },

        /**
         * Overrides to restore the left property and the scrollTop on the updated
         * column, and to enable the swipe handlers
         *
         * @override
         */
        updateColumn: function (localID) {
            var index = _.findIndex(this.widgets, {db_id: localID});
            var $column = this.widgets[index].$el;
            var scrollTop = $column.scrollTop();
            return (
                this._super
                    .apply(this, arguments)
                    .then(() => this._layoutUpdate(false))
                    // Required when clicking on 'Load More'
                    .then(() => $column.scrollTop(scrollTop))
                    .then(() => this._enableSwipe())
            );
        },

        // --------------------------------------------------------------------------
        // Private
        // --------------------------------------------------------------------------

        /**
         * Check if we use the quick create on mobile
         * @returns {Boolean}
         * @private
         */
        _canCreateColumn: function () {
            return this.quickCreateEnabled && this.quickCreate && this.widgets.length;
        },

        /**
         * Update the columns positions
         *
         * @private
         * @param {Boolean} [animate=false] set to true to animate
         */
        _computeColumnPosition: function (animate) {
            if (this.widgets.length) {
                // Check rtl to compute correct css value
                const rtl = _t.database.parameters.direction === "rtl";

                // Display all o_kanban_group
                this.$(".o_kanban_group").show();

                const $columnAfter = this._toNode(
                    this.widgets.filter(
                        (widget, index) => index > this.activeColumnIndex
                    )
                );
                const promiseAfter = this._updateColumnCss(
                    $columnAfter,
                    rtl ? {right: "100%"} : {left: "100%"},
                    animate
                );

                const $columnBefore = this._toNode(
                    this.widgets.filter(
                        (widget, index) => index < this.activeColumnIndex
                    )
                );
                const promiseBefore = this._updateColumnCss(
                    $columnBefore,
                    rtl ? {right: "-100%"} : {left: "-100%"},
                    animate
                );

                const $columnCurrent = this._toNode(
                    this.widgets.filter(
                        (widget, index) => index === this.activeColumnIndex
                    )
                );
                const promiseCurrent = this._updateColumnCss(
                    $columnCurrent,
                    rtl ? {right: "0%"} : {left: "0%"},
                    animate
                );

                promiseAfter
                    .then(promiseBefore)
                    .then(promiseCurrent)
                    .then(() => {
                        $columnAfter.hide();
                        $columnBefore.hide();
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
                this.$(
                    ".o_kanban_mobile_tab.o_current, .o_kanban_group.o_current"
                ).removeClass("o_current");
                this.$(
                    '.o_kanban_group[data-id="' +
                        columnID +
                        '"], ' +
                        '.o_kanban_mobile_tab[data-id="' +
                        columnID +
                        '"]'
                ).addClass("o_current");
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
                    // Apply
                    if (moveToIndex !== lastItemIndex && i === moveToIndex - 1) {
                        var partialWidth = 0.75;
                        scrollToLeft += columnWidth * partialWidth;
                    } else {
                        scrollToLeft += columnWidth;
                    }
                }
                // Apply the scroll x on the tabs
                // XXX in case of RTL, should we use scrollRight?
                this.$(".o_kanban_mobile_tabs").scrollLeft(scrollToLeft);
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
                var $tabs = this.$(".o_kanban_mobile_tabs");
                $tabs.toggleClass(
                    "justify-content-between",
                    $tabs.outerWidth() >= widthChilds
                );
            }
        },

        /**
         * Enables swipe event on the current column
         *
         * @private
         */
        _enableSwipe: function () {
            var self = this;
            var step = _t.database.parameters.direction === "rtl" ? -1 : 1;
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
                },
            });
        },

        /**
         * Retrieve the outerWidth of a given widget column
         *
         * @param {KanbanColumn} column
         * @returns {integer} outerWidth of the found column
         * @private
         */
        _getTabWidth: function (column) {
            var columnID = column.id || column.db_id;
            return this.$(
                '.o_kanban_mobile_tab[data-id="' + columnID + '"]'
            ).outerWidth();
        },

        /**
         * Update the kanban layout
         *
         * @private
         * @param {Boolean} [animate=false] set to true to animate
         */
        _layoutUpdate: function (animate) {
            this._computeCurrentColumn();
            this._computeTabPosition();
            this._computeColumnPosition(animate);
            this._enableSwipe();
        },

        /**
         * Moves to the given kanban column
         *
         * @private
         * @param {integer} moveToIndex index of the column to move to
         * @param {Boolean} [animate=false] set to true to animate
         * @returns {Promise} resolved when the new current group has been loaded
         *   and displayed
         */
        _moveToGroup: function (moveToIndex, animate) {
            if (this.widgets.length === 0) {
                return Promise.resolve();
            }
            var self = this;
            if (moveToIndex >= 0 && moveToIndex < this.widgets.length) {
                this.activeColumnIndex = moveToIndex;
            }
            var column = this.widgets[this.activeColumnIndex];
            this._enableSwipe();
            if (!column.data.isOpen) {
                this.trigger_up("column_toggle_fold", {
                    db_id: column.db_id,
                    onSuccess: () => self._layoutUpdate(animate),
                });
            } else {
                this._layoutUpdate(animate);
            }
            return Promise.resolve();
        },
        /**
         * @override
         * @private
         */
        _renderExampleBackground: function () {
            // Override to avoid display of example background
        },
        /**
         * @override
         * @private
         */
        _renderGrouped: function (fragment) {
            var self = this;
            var newFragment = document.createDocumentFragment();
            this._super.apply(this, [newFragment]);
            this.defs.push(
                Promise.all(this.defs).then(function () {
                    var data = [];
                    _.each(self.state.data, function (group) {
                        if (!group.value) {
                            group = _.extend({}, group, {value: _t("Undefined")});
                            data.unshift(group);
                        } else {
                            data.push(group);
                        }
                    });

                    var kanbanColumnContainer = document.createElement("div");
                    kanbanColumnContainer.classList.add("o_kanban_columns_content");
                    kanbanColumnContainer.appendChild(newFragment);
                    fragment.appendChild(kanbanColumnContainer);
                    $(
                        qweb.render("KanbanView.MobileTabs", {
                            data: data,
                            quickCreateEnabled: self._canCreateColumn(),
                        })
                    ).prependTo(fragment);
                })
            );
        },

        /**
         * @override
         * @private
         */
        _renderView: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (self.state.groupedBy.length) {
                    // Force first column for kanban view, because the groupedBy can be changed
                    return self._moveToGroup(0);
                }
                if (self._canCreateColumn()) {
                    self._onMobileQuickCreateClicked();
                }
                return Promise.resolve();
            });
        },

        /**
         * Retrieve the Jquery node (.o_kanban_group) for a list of a given widgets
         *
         * @private
         * @param widgets
         * @returns {jQuery} the matching .o_kanban_group widgets
         */
        _toNode: function (widgets) {
            const selectorCss = widgets
                .map(
                    (widget) =>
                        '.o_kanban_group[data-id="' + (widget.id || widget.db_id) + '"]'
                )
                .join(", ");
            return this.$(selectorCss);
        },

        /**
         * Update the given column to the updated positions
         *
         * @private
         * @param $column The jquery column
         * @param cssProperties Use to update column
         * @param {Boolean} [animate=false] set to true to animate
         * @returns {Promise}
         */
        _updateColumnCss: function ($column, cssProperties, animate) {
            if (animate) {
                return new Promise((resolve) =>
                    $column.animate(cssProperties, "fast", resolve)
                );
            }
            $column.css(cssProperties);
            return Promise.resolve();
        },

        // --------------------------------------------------------------------------
        // Handlers
        // --------------------------------------------------------------------------

        /**
         * @private
         */
        _onColumnAdded: function () {
            this._computeTabPosition();
            if (this._canCreateColumn() && !this.quickCreate.folded) {
                this.quickCreate.toggleFold();
            }
        },

        /**
         * @private
         */
        _onMobileQuickCreateClicked: function (event) {
            if (event) {
                event.stopPropagation();
            }
            this.quickCreate.toggleFold();
            this.$(".o_kanban_group").toggle(this.quickCreate.folded);
        },
        /**
         * @private
         * @param {MouseEvent} event
         */
        _onMobileTabClicked: function (event) {
            if (this._canCreateColumn() && !this.quickCreate.folded) {
                this.quickCreate.toggleFold();
            }
            this._moveToGroup($(event.currentTarget).index(), true);
        },
        /**
         * @private
         * @override
         */
        _onCloseQuickCreate: function () {
            if (this.widgets.length && !this.quickCreate.folded) {
                this.$(".o_kanban_group").toggle(true);
                this.quickCreate.toggleFold();
            }
        },
    });
});
