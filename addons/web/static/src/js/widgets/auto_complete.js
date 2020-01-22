odoo.define('web.AutoComplete', function (require) {
"use strict";

var Widget = require('web.Widget');

return Widget.extend({
    template: "SearchView.autocomplete",

    // Parameters for autocomplete constructor:
    //
    // parent: this is used to detect keyboard events
    //
    // options.source: function ({term:query}, callback).  This function will be called to
    //      obtain the search results corresponding to the query string.  It is assumed that
    //      options.source will call callback with the results.
    // options.select: function (ev, {item: {facet:facet}}).  Autocomplete widget will call
    //      that function when a selection is made by the user
    // options.get_search_string: function ().  This function will be called by autocomplete
    //      to obtain the current search string.
    init: function (parent, options) {
        this._super(parent);
        this.$input = parent.$el;
        this.source = options.source;
        this.select = options.select;
        this.get_search_string = options.get_search_string;

        this.current_result = null;

        this.searching = true;
        this.search_string = '';
        this.current_search = null;
        this._isInputComposing = false;
    },
    start: function () {
        var self = this;
        this.$input.on('compositionend', function (ev) {
            self._isInputComposing = false;
        });
        this.$input.on('compositionstart', function (ev) {
            self._isInputComposing = true;
        });
        this.$input.on('keyup', function (ev) {
            if (ev.which === $.ui.keyCode.RIGHT && !self._isInputComposing) {
                self.searching = true;
                ev.preventDefault();
                return;
            }
            if (ev.which === $.ui.keyCode.ENTER && !self._isInputComposing) {
                if (self.search_string.length) {
                    self.select_item(ev);
                }
                return;
            }
            self._updateSearch();
        });
        this.$input.on('input', function (ev) {
            if (ev.originalEvent.inputType === 'insertCompositionText') {
                // click inside keyboard IME suggestions menu
                self._updateSearch();
            }
        });
        this.$input.on('keypress', function (ev) {
            self.search_string = self.search_string + String.fromCharCode(ev.which);
            if (self.search_string.length) {
                self.searching = true;
                var search_string = self.search_string;
                self.initiate_search(search_string);
            } else {
                self.close();
            }
        });
        this.$input.on('keydown', function (ev) {
            if (self._isInputComposing) {
                return;
            }
            switch (ev.which) {
                case $.ui.keyCode.ENTER:

                // TAB and direction keys are handled at KeyDown because KeyUp
                // is not guaranteed to fire.
                // See e.g. https://github.com/aef-/jquery.masterblaster/issues/13
                case $.ui.keyCode.TAB:
                    if (self.search_string.length) {
                        self.select_item(ev);
                    }
                    break;
                case $.ui.keyCode.DOWN:
                    self.move('down');
                    self.searching = false;
                    ev.preventDefault();
                    break;
                case $.ui.keyCode.UP:
                    self.move('up');
                    self.searching = false;
                    ev.preventDefault();
                    break;
                case $.ui.keyCode.RIGHT:
                    self.searching = false;
                    var current = self.current_result;
                    if (current && current.expand && !current.expanded) {
                        self.expand();
                        self.searching = true;
                    }
                    ev.preventDefault();
                    break;
                case $.ui.keyCode.ESCAPE:
                    self.close();
                    self.searching = false;
                    break;
            }
        });
    },
    initiate_search: function (query) {
        if (query === this.search_string && query !== this.current_search) {
            this.search(query);
        }
    },
    search: function (query) {
        var self = this;
        this.current_search = query;
        this.source({term:query}, function (results) {
            if (results.length) {
                self.render_search_results(results);
                self.focus_element(self.$('li:first-child'));
            } else {
                self.close();
            }
        });
    },
    render_search_results: function (results) {
        var self = this;
        var $list = this.$el;
        $list.empty();
        results.forEach(function (result) {
            var $item = self.make_list_item(result).appendTo($list);
            result.$el = $item;
        });
        // IE9 doesn't support addEventListener with option { once: true }
        this.el.onmousemove = function (ev) {
            self.$('li').each(function (index, li) {
                li.onmouseenter = self.focus_element.bind(self, $(li));
            });
            var targetFocus = ev.target.tagName === 'LI' ?
                ev.target :
                ev.target.closest('li');
            self.focus_element($(targetFocus));
            self.el.onmousemove = null;
        };
        this.show();
    },
    make_list_item: function (result) {
        var self = this;
        var $li = $('<li>')
            .mousedown(function (ev) {
                if (ev.button === 0) { // left button
                    self.select(ev, {item: {facet: result.facet}});
                    self.close();
                }
            })
            .data('result', result);
        if (result.expand) {
            var $expand = $('<a class="o-expand" href="#">').appendTo($li);
            $expand.mousedown(function (ev) {
                ev.stopPropagation();
                ev.preventDefault(); // to prevent dropdown from closing
                if (result.expanded) {
                    self.fold();
                } else {
                    self.expand();
                }
            });
            $expand.click(function(ev) {
                ev.preventDefault(); // to prevent url from changing due to href="#"
            });
            result.expanded = false;
        }
        if (result.indent) $li.addClass('o-indent');
        $li.append($('<a href="#">').html(result.label));
        return $li;
    },
    expand: function () {
        var self = this;
        var current_result = this.current_result;
        current_result.expand(this.get_search_string()).then(function (results) {
            (results || [{label: '(no result)'}]).reverse().forEach(function (result) {
                result.indent = true;
                var $li = self.make_list_item(result);
                current_result.$el.after($li);
            });
            self.current_result.expanded = true;
            self.current_result.$el.find('a.o-expand').removeClass('o-expand').addClass('o-expanded');
        });
    },
    fold: function () {
        var $next = this.current_result.$el.next();
        while ($next.hasClass('o-indent')) {
            $next.remove();
            $next = this.current_result.$el.next();
        }
        this.current_result.expanded = false;
        this.current_result.$el.find('a.o-expanded').removeClass('o-expanded').addClass('o-expand');
    },
    focus_element: function ($li) {
        this.$('li').removeClass('o-selection-focus');
        $li.addClass('o-selection-focus');
        this.current_result = $li.data('result');
    },
    select_item: function (ev) {
        if (this.current_result.facet) {
            this.select(ev, {item: {facet: this.current_result.facet}});
            this.close();
        }
    },
    show: function () {
        this.$el.show();
    },
    close: function () {
        this.current_search = null;
        this.search_string = '';
        this.searching = true;
        this.$el.hide();
    },
    move: function (direction) {
        var $next;
        if (direction === 'down') {
            $next = this.$('li.o-selection-focus').next();
            if (!$next.length) $next = this.$('li').first();
        } else {
            $next = this.$('li.o-selection-focus').prev();
            if (!$next.length) $next = this.$('li').last();
        }
        this.focus_element($next);
    },
    is_expandable: function () {
        return !!this.$('.o-selection-focus .o-expand').length;
    },
    is_expanded: function() {
        return this.$el[0].style.display === "block";
    },
    /**
     * Update search dropdown menu based on new input content.
     *
     * @private
     */
    _updateSearch: function () {
        var search_string = this.get_search_string();
        if (this.search_string !== search_string) {
            if (search_string.length) {
                this.search_string = search_string;
                this.initiate_search(search_string);
            } else {
                this.close();
            }
        }
    },
});
});
