odoo.define('mail/static/src/components/category_chat_item/category_chat_item.js', function (require) {
'use strict';

const components = {
    CategoryItem: require('mail/static/src/components/category_item/category_item.js'),
    PartnerImStatusIcon: require('mail/static/src/components/partner_im_status_icon/partner_im_status_icon.js'),
    EditableText: require('mail/static/src/components/editable_text/editable_text.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class CategoryChatItem extends Component {
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
                threadCorrespondent: thread && thread.correspondent ? thread.correspondent.__state : undefined,
            }
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {String}
     */
    get image() {
        return this.thread.correspondent.avatarUrl;
    }

    /**
     * @return {mail.thread}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

    /**
     * @returns {mail.discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.discuss;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRename(ev) {
        ev.stopPropagation()
        this.discuss.setThreadRenaming(this.thread);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUnpin(ev) {
        ev.stopPropagation();
        this.thread.unsubscribe();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onCancelRenaming(ev) {
        this.discuss.cancelThreadRenaming(this.thread);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickedEditableText(ev) {
        ev.stopPropagation();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {String} ev.detail.newName
     */
    _onValidateEditableText(ev) {
        ev.stopPropagation();
        this.discuss.renameThread(this.thread, ev.detail.newName);
    }
}

Object.assign(CategoryChatItem, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.CategoryChatItem',
});

return CategoryChatItem;

});
