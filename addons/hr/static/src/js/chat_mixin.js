odoo.define('hr.chat_mixin', function (require) {
"use strict";

const { Component } = owl;

// CHAT MIXIN
const ChatMixin = {
    /**
     * @override
     */
    _render: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var $chat_button = self.$el.find('.o_employee_chat_btn');
            $chat_button.off('click').on('click', self._onOpenChat.bind(self));
        });
    },

    destroy: function () {
        if (this.$el) {
            this.$el.find('.o_employee_chat_btn').off('click');
        }
        return this._super();
    },

    async _onOpenChat(ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        const messaging = await Component.env.services.messaging.get();
        messaging.openChat({ employeeId: this.state.data.id });
        return true;
    },
};

return ChatMixin;
});
