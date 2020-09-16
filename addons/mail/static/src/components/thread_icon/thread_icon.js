odoo.define('mail/static/src/components/thread_icon/thread_icon.js', function (require) {
'use strict';

const components = {
    ThreadTypingIcon: require('mail/static/src/components/thread_typing_icon/thread_typing_icon.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;

class ThreadIcon extends Component {

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

Object.assign(ThreadIcon, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.ThreadIcon',
});

return ThreadIcon;

});
