/** @odoo-module **/

import useStore from '@mail/component_hooks/use_store/use_store';
import CategoryItem from '@mail/components/category_item/category_item';
import PartnerImStatusIcon from '@mail/components/partner_im_status_icon/partner_im_status_icon';

const { Component } = owl;

const components = { CategoryItem, PartnerImStatusIcon };

class CategoryLivechatItem extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                thread: thread ? thread.__state : undefined,
                threadCorrespondent: thread && thread.correspondent ? thread.correspondent.__state : undefined,
            }
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get image() {
        if (this.thread.correspondent && this.thread.correspondent.id > 0) {
            return this.thread.correspondent.avatarUrl;
        }
        return '/mail/static/src/img/smiley/avatar.jpg';
    }

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     *
     * @param {MouseEvent} ev
     */
    _onClickUnpin(ev) {
        ev.stopPropagation();
        this.thread.unsubscribe();
    }

}

Object.assign(CategoryLivechatItem, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'im_livechat.CategoryLivechatItem',
});

export default CategoryLivechatItem;
