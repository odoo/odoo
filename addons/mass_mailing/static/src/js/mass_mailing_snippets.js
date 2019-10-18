odoo.define('mass_mailing.snippets.options', function (require) {
"use strict";

var options = require('web_editor.snippets.options');

// Snippet option for resizing  image and column width inline like excel
options.registry.mass_mailing_sizing_x = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        this.containerWidth = this.$target.parent().closest("td, table, div").width();

        var self = this;
        var offset, sib_offset, target_width, sib_width;

        this.$overlay.find(".o_handle.e, .o_handle.w").removeClass("readonly");
        this.isIMG = this.$target.is("img");
        if (this.isIMG) {
            this.$overlay.find(".o_handle.w").addClass("readonly");
        }

        var $body = $(this.ownerDocument.body);
        this.$overlay.find(".o_handle").on('mousedown', function (event) {
            event.preventDefault();
            var $handle = $(this);
            var compass = false;

            _.each(['n', 's', 'e', 'w'], function (handler) {
                if ($handle.hasClass(handler)) { compass = handler; }
            });
            if (self.isIMG) { compass = "image"; }

            $body.on("mousemove.mass_mailing_width_x", function (event) {
                event.preventDefault();
                offset = self.$target.offset().left;
                target_width = self.get_max_width(self.$target);
                if (compass === 'e' && self.$target.next().offset()) {
                    sib_width = self.get_max_width(self.$target.next());
                    sib_offset = self.$target.next().offset().left;
                    self.change_width(event, self.$target, target_width, offset, true);
                    self.change_width(event, self.$target.next(), sib_width, sib_offset, false);
                }
                if (compass === 'w' && self.$target.prev().offset()) {
                    sib_width = self.get_max_width(self.$target.prev());
                    sib_offset = self.$target.prev().offset().left;
                    self.change_width(event, self.$target, target_width, offset, false);
                    self.change_width(event, self.$target.prev(), sib_width, sib_offset, true);
                }
                if (compass === 'image') {
                    self.change_width(event, self.$target, target_width, offset, true);
                }
            });
            $body.one("mouseup", function () {
                $body.off('.mass_mailing_width_x');
            });
        });

        return def;
    },
    change_width: function (event, target, target_width, offset, grow) {
        target.css("width", grow ? (event.pageX - offset) : (offset + target_width - event.pageX));
        this.trigger_up('cover_update');
    },
    get_int_width: function (el) {
        return parseInt($(el).css("width"), 10);
    },
    get_max_width: function ($el) {
        return this.containerWidth - _.reduce(_.map($el.siblings(), this.get_int_width), function (memo, w) { return memo + w; });
    },
    onFocus: function () {
        this._super.apply(this, arguments);

        if (this.$target.is("td, th")) {
            this.$overlay.find(".o_handle.e, .o_handle.w").toggleClass("readonly", this.$target.siblings().length === 0);
        }
    },
});

options.registry.mass_mailing_table_item = options.Class.extend({
    onClone: function (options) {
        this._super.apply(this, arguments);

        // If we cloned a td or th element...
        if (options.isCurrent && this.$target.is("td, th")) {
            // ... and that the td or th element was alone on its row ...
            if (this.$target.siblings().length === 1) {
                var $tr = this.$target.parent();
                $tr.clone().empty().insertAfter($tr).append(this.$target); // ... move the clone in a new row instead
                return;
            }

            // ... if not, if the clone neighbor is an empty cell, remove this empty cell (like if the clone content had been put in that cell)
            var $next = this.$target.next();
            if ($next.length && $next.text().trim() === "") {
                $next.remove();
                return;
            }

            // ... if not, insert an empty col in each other row, at the index of the clone
            var width = this.$target.width();
            var $trs = this.$target.closest("table").children("thead, tbody, tfoot").addBack().children("tr").not(this.$target.parent());
            _.each($trs.children(":nth-child(" + this.$target.index() + ")"), function (col) {
                $(col).after($("<td/>", {style: "width: " + width + "px;"}));
            });
        }
    },
    onRemove: function () {
        this._super.apply(this, arguments);

        // If we are removing a td or th element which was not alone on its row ...
        if (this.$target.is("td, th") && this.$target.siblings().length > 0) {
            var $trs = this.$target.closest("table").children("thead, tbody, tfoot").addBack().children("tr").not(this.$target.parent());
            if ($trs.length) { // ... if there are other rows in the table ...
                var $last_tds = $trs.children(":last-child");
                if (_.reduce($last_tds, function (memo, td) { return memo + (td.innerHTML || ""); }, "").trim() === "") {
                    $last_tds.remove(); // ... remove the potential full empty column in the table
                } else {
                    this.$target.parent().append("<td/>"); // ... else, if there is no full empty column, append an empty col in the current row
                }
            }
        }
    },
});

// Adding compatibility for the outlook compliance of mailings.
// Commit of such compatibility : a14f89c8663c9cafecb1cc26918055e023ecbe42
options.registry.background = options.registry.background.extend({
    start: function () {
        this._super();
        if (this.snippets && this.snippets.split('.')[0] === "mass_mailing") {
            var $table_target = this.$target.find('table:first');
            if ($table_target.length) {
                this.$target = $table_target;
            }
        }
    }
});
});
