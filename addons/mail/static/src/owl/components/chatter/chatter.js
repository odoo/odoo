odoo.define('mail.component.Chatter', function (require) {
'use strict';

const AttachmentBox = require('mail.component.AttachmentBox');
const ChatterTopbar = require('mail.component.ChatterTopbar');
const Thread = require('mail.component.Thread');

const { Component, useState } = owl;
const { useDispatch, useGetters, useRef, useStore } = owl.hooks;

class Chatter extends Component {
    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.state = useState({ isAttachmentBoxVisible: false });
        this.storeDispatch = useDispatch();
        this.storeGetters = useGetters();
        this.storeProps = useStore((state, props) => {
            const thread = this.storeGetters.thread({
                _model: props.model,
                id: props.id,
            });
            return {
                threadLocalId: thread ? thread.localId : undefined,
            };
        });
        this._threadRef = useRef('thread');
    }

    mounted() {
        // TODO {xdu}
        // Need to say to the underlying Thread that there is no long polling
        // So when doing message_post, you need to do a read on the record and
        // then verify in the message_ids if there are missing messages or not
        // and then make a message_format call for each message (including the
        // one posted)
        this.storeDispatch('initChatter', {
            model: this.props.model,
            id: this.props.id,
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onTopbarSelectAttachment(ev) {
        this.state.isAttachmentBoxVisible = !this.state.isAttachmentBoxVisible;
    }
}

Chatter.components = { AttachmentBox, ChatterTopbar, Thread };

Chatter.props = {
    id: Number,
    model: String
};

Chatter.template = 'mail.component.Chatter';

return Chatter;

});
