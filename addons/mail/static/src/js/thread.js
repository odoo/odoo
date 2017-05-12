odoo.define('mail.ChatThread', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var ORDER = {
    ASC: 1,
    DESC: -1,
};

var read_more = _t('read more');
var read_less = _t('read less');

function time_from_now(date) {
    if (moment().diff(date, 'seconds') < 45) {
        return _t("now");
    }
    return date.fromNow();
}

var Thread = Widget.extend({
    className: 'o_mail_thread',

    events: {
        "click a": "on_click_redirect",
        "click img": "on_click_redirect",
        "click strong": "on_click_redirect",
        "click .o_thread_show_more": "on_click_show_more",
        "click .o_thread_message_needaction": function (event) {
            var message_id = $(event.currentTarget).data('message-id');
            this.trigger("mark_as_read", message_id);
        },
        "click .o_thread_message_star": function (event) {
            var message_id = $(event.currentTarget).data('message-id');
            this.trigger("toggle_star_status", message_id);
        },
        "click .o_thread_message_reply": function (event) {
            this.selected_id = $(event.currentTarget).data('message-id');
            this.$('.o_thread_message').removeClass('o_thread_selected_message');
            this.$('.o_thread_message[data-message-id="' + this.selected_id + '"]')
                .addClass('o_thread_selected_message');
            this.trigger('select_message', this.selected_id);
            event.stopPropagation();
        },
        "click .oe_mail_expand": function (event) {
            event.preventDefault();
            var $message = $(event.currentTarget).parents('.o_thread_message');
            $message.addClass('o_message_expanded');
            this.expanded_msg_ids.push($message.data('message-id'));
        },
        "click .o_thread_message": function (event) {
            $(event.currentTarget).toggleClass('o_thread_selected_message');
        },
        "click": function () {
            if (this.selected_id) {
                this.unselect();
                this.trigger('unselect_message');
            }
        },
    },

    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = _.defaults(options || {}, {
            display_order: ORDER.ASC,
            display_needactions: true,
            display_stars: true,
            display_document_link: true,
            display_avatar: true,
            squash_close_messages: true,
            display_email_icon: true,
            display_reply_icon: false,
        });
        this.expanded_msg_ids = [];
        this.selected_id = null;
    },

    render: function (messages, options) {
        var self = this;
        var msgs = _.map(messages, this._preprocess_message.bind(this));
        if (this.options.display_order === ORDER.DESC) {
            msgs.reverse();
        }
        options = _.extend({}, this.options, options);

        // Hide avatar and info of a message if that message and the previous
        // one are both comments wrote by the same author at the same minute
        // and in the same document (users can now post message in documents
        // directly from a channel that follows it)
        var prev_msg;
        _.each(msgs, function (msg) {
            if (!prev_msg || (Math.abs(msg.date.diff(prev_msg.date)) > 60000) ||
                prev_msg.message_type !== 'comment' || msg.message_type !== 'comment' ||
                (prev_msg.author_id[0] !== msg.author_id[0]) || prev_msg.model !== msg.model ||
                prev_msg.res_id !== msg.res_id) {
                msg.display_author = true;
            } else {
                msg.display_author = !options.squash_close_messages;
            }
            prev_msg = msg;
        });

        this.$el.html(QWeb.render('mail.ChatThread', {
            messages: msgs,
            options: options,
            ORDER: ORDER,
        }));

        _.each(msgs, function(msg) {
            var $msg = self.$('.o_thread_message[data-message-id="'+ msg.id +'"]');
            $msg.find('.o_mail_timestamp').data('date', msg.date);

            self.insert_read_more($msg);
        });

        if (!this.update_timestamps_interval) {
            this.update_timestamps_interval = setInterval(function() {
                self.update_timestamps();
            }, 1000*60);
        }
    },

    /**
     *  Modifies $element to add the 'read more/read less' functionality
     *  All element nodes with "data-o-mail-quote" attribute are concerned.
     *  All text nodes after a ""#stopSpelling" element are concerned.
     *  Those text nodes need to be wrapped in a span (toggle functionality).
     *  All consecutive elements are joined in one 'read more/read less'.
     */
    insert_read_more: function ($element) {
        var self = this;

        var groups = [];
        var read_more_nodes;

        // nodeType 1: element_node
        // nodeType 3: text_node
        var $children = $element.contents()
            .filter(function() {
                return this.nodeType === 1 || this.nodeType === 3 && this.nodeValue.trim();
            });

        _.each($children, function(child) {
            var $child = $(child);

            // Hide Text nodes if "stopSpelling"
            if (child.nodeType === 3 && $child.prevAll("[id*='stopSpelling']").length > 0) {
                // Convert Text nodes to Element nodes
                var $child = $('<span>', {
                    text: child.textContent,
                    "data-o-mail-quote": "1",
                });
                child.parentNode.replaceChild($child[0], child);
            }

            // Create array for each "read more" with nodes to toggle
            if ($child.attr('data-o-mail-quote') || ($child.get(0).nodeName === 'BR' && $child.prev("[data-o-mail-quote='1']").length > 0)) {
                if (!read_more_nodes) {
                    read_more_nodes = [];
                    groups.push(read_more_nodes);
                }
                $child.hide();
                read_more_nodes.push($child);
            } else {
                read_more_nodes = undefined;
                self.insert_read_more($child);
            }
        });

        _.each(groups, function(group) {
            // Insert link just before the first node
            var $read_more = $('<a>', {
                class: "o_mail_read_more",
                href: "#",
                text: read_more,
            }).insertBefore(group[0]);

            // Toggle All next nodes
            var is_read_more = true;
            $read_more.click(function(e) {
                e.preventDefault();
                is_read_more = !is_read_more;
                _.each(group, function ($child) {
                    $child.hide();
                    $child.toggle(!is_read_more);
                });
                $read_more.text(is_read_more ? read_more : read_less);
            });
        });
    },
    update_timestamps: function () {
        this.$('.o_mail_timestamp').each(function() {
            var date = $(this).data('date');
            $(this).html(time_from_now(date));
        });
    },
    on_click_redirect: function (event) {
        var id = $(event.target).data('oe-id');
        if (id) {
            event.preventDefault();
            var model = $(event.target).data('oe-model');
            var options = model && (model !== 'mail.channel') ? {model: model, id: id} : {channel_id: id};
            this._redirect(options);
        }
    },

    _redirect: _.debounce(function (options) {
        if ('channel_id' in options) {
            this.trigger('redirect_to_channel', options.channel_id);
        } else {
            this.trigger('redirect', options.model, options.id);
        }
    }, 200, true),

    on_click_show_more: function () {
        this.trigger('load_more_messages');
    },

    _preprocess_message: function (message) {
        var msg = _.extend({}, message);

        msg.date = moment.min(msg.date, moment());
        msg.hour = time_from_now(msg.date);

        var date = msg.date.format('YYYY-MM-DD');
        if (date === moment().format('YYYY-MM-DD')) {
            msg.day = _t("Today");
        } else if (date === moment().subtract(1, 'days').format('YYYY-MM-DD')) {
            msg.day = _t("Yesterday");
        } else {
            msg.day = msg.date.format('LL');
        }

        if (_.contains(this.expanded_msg_ids, message.id)) {
            msg.expanded = true;
        }

        msg.display_subject = message.subject && message.message_type !== 'notification' && !(message.model && (message.model !== 'mail.channel'));
        msg.is_selected = msg.id === this.selected_id;
        return msg;
    },

    /**
     * Removes a message and re-renders the thread
     * @param {int} [message_id] the id of the removed message
     * @param {array} [messages] the list of messages to display, without the removed one
     * @param {object} [options] options for the thread rendering
     */
    remove_message_and_render: function (message_id, messages, options) {
        var self = this;
        var done = $.Deferred();
        this.$('.o_thread_message[data-message-id="' + message_id + '"]').fadeOut({
            done: function () { self.render(messages, options); done.resolve();},
            duration: 200,
        });
        return done;
    },

    /**
     * Scrolls the thread to a given message or offset if any, to bottom otherwise
     * @param {int} [options.id] optional: the id of the message to scroll to
     * @param {int} [options.offset] optional: the number of pixels to scroll
     */
    scroll_to: function (options) {
        options = options || {};
        if (options.id !== undefined) {
            var $target = this.$('.o_thread_message[data-message-id="' + options.id + '"]');
            if (options.only_if_necessary) {
                var delta = $target.parent().height() - $target.height();
                var offset = delta < 0 ? 0 : delta - ($target.offset().top - $target.offsetParent().offset().top);
                offset = - Math.min(offset, 0);
                this.$el.scrollTo("+=" + offset + "px", options);
            } else if ($target.length) {
                this.$el.scrollTo($target);
            }
        } else if (options.offset !== undefined) {
            this.$el.scrollTop(options.offset);
        } else {
            this.$el.scrollTop(this.el.scrollHeight);
        }
    },
    get_scrolltop: function () {
        return this.$el.scrollTop();
    },
    is_at_bottom: function () {
        return this.el.scrollHeight - this.$el.scrollTop() - this.$el.outerHeight() < 5;
    },
    unselect: function () {
        this.$('.o_thread_message').removeClass('o_thread_selected_message');
        this.selected_id = null;
    },
    destroy: function () {
        clearInterval(this.update_timestamps_interval);
    },
});

Thread.ORDER = ORDER;

return Thread;

});
