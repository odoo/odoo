odoo.define('im_livechat.thread_window', function (require) {
"use strict";

var core = require('web.core');
const ThreadWindow = require('mail.ThreadWindow');

var QWeb = core.qweb;

ThreadWindow.include({
    /**
     * @override
     * @private
     * @param {integer|string} threadID
     */
    _onUpdateTypingPartners(threadID) {
        this._super.apply(this, arguments);
        this.$('.o_thread_message_preview').replaceWith(QWeb.render('mail.widget.Thread.TypingData', {thread: this._thread}));
    },
});

});
