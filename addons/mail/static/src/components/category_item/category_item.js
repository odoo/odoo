odoo.define('mail/static/src/components/category_item/category_item.js', function (require) {
'use strict';

const components = {
    ThreadIcon: require('mail/static/src/components/thread_icon/thread_icon.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const { isEventHandled } = require('mail/static/src/utils/utils.js');

const { Component } = owl;

class CategoryItem extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const discuss = this.env.messaging.discuss;
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                discuss: discuss ? discuss.__state : undefined,
                thread: thread ? thread.__state : undefined,
            };
        })
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.discuss;
    }

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

    /**
     * @returns {integer}
     */
    get unreadCounter() {
        if (this.thread.model === 'mail.box') {
            return this.thread.counter;
        } else if (this.thread.channel_type === 'channel') {
            return this.thread.message_needaction_counter;
        } else if (this.thread.isChatChannel) {
            return this.thread.localMessageUnreadCounter;
        }
        return 0;

    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        if (isEventHandled(ev, 'EditableText.click')) {
            return;
        }
        this.thread.open();
    }

}

Object.assign(CategoryItem, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.CategoryItem',
});

return CategoryItem;

});
