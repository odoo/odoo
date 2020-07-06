odoo.define('mail/static/src/components/record_status_icon/record_status_icon.js', function (require) {
'use strict';

const components = {
    ThreadTypingIcon: require('mail/static/src/components/thread_typing_icon/thread_typing_icon.js'),
};

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class RecordStatusIcon extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const record = this.env.models[props.recordModel] && this.env.models[props.recordModel].get(props.recordLocalId);
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                record: record ? record.__state : undefined,
                partnerRoot: this.env.messaging.partnerRoot
                    ? this.env.messaging.partnerRoot.__state
                    : undefined,
                thread: thread ? thread.__state : undefined,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Boolean}
     */
    get isTyping() {
        return this.thread && this.thread.orderedOtherTypingMembers.length > 0;
    }

    /**
     * @returns {mail.model}
     */
    get record() {
        return this.env.models[this.props.recordModel]
            && this.env.models[this.props.recordModel].get(this.props.recordLocalId);
    }

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

}

Object.assign(RecordStatusIcon, {
    components,
    defaultProps: {
        hasBackground: true
    },
    props: {
        hasBackground: Boolean,
        recordLocalId: String,
        recordModel: String,
        threadLocalId: {
            optional: true,
            type: String,
        }
    },
    template: 'mail.RecordStatusIcon',
});

return RecordStatusIcon;

});
