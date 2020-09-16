odoo.define('mail/static/src/components/thread_textual_typing_status/thread_textual_typing_status.js', function (require) {
'use strict';

const components = {
    ThreadTypingIcon: require('mail/static/src/components/thread_typing_icon/thread_typing_icon.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;

class ThreadTextualTypingStatus extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

}

Object.assign(ThreadTextualTypingStatus, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.ThreadTextualTypingStatus',
});

return ThreadTextualTypingStatus;

});
