odoo.define('mail/static/src/components/chatter_topbar/chatter_topbar.js', function (require) {
'use strict';

const components = {
    FollowButton: require('mail/static/src/components/follow_button/follow_button.js'),
    FollowerListMenu: require('mail/static/src/components/follower_list_menu/follower_list_menu.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class ChatterTopbar extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const chatter = this.env.models['mail.chatter'].get(props.chatterLocalId);
            const thread = chatter ? chatter.thread : undefined;
            const threadAttachments = thread ? thread.allAttachments : [];
            return {
                areThreadAttachmentsLoaded: thread && thread.areAttachmentsLoaded,
                chatter: chatter ? chatter.__state : undefined,
                composer: chatter && chatter.composer ? chatter.composer.__state : undefined,
                threadAttachmentsAmount: threadAttachments.length,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.chatter}
     */
    get chatter() {
        return this.env.models['mail.chatter'].get(this.props.chatterLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAttachments(ev) {
        this.chatter.update({
            isAttachmentBoxVisible: !this.chatter.isAttachmentBoxVisible,
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickClose(ev) {
        this.trigger('o-close-chatter');
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickLogNote(ev) {
        if (!this.chatter.composer) {
            return;
        }
        if (this.chatter.isComposerVisible && this.chatter.composer.isLog) {
            this.chatter.update({ isComposerVisible: false });
        } else {
            this.chatter.showLogNote();
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickScheduleActivity(ev) {
        const action = {
            type: 'ir.actions.act_window',
            name: this.env._t("Schedule Activity"),
            res_model: 'mail.activity',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_res_id: this.chatter.thread.id,
                default_res_model: this.chatter.thread.model,
            },
            res_id: false,
        };
        return this.env.bus.trigger('do-action', {
            action,
            options: {
                on_close: () => {
                    this.chatter.thread.refreshActivities();
                    this.chatter.thread.refresh();
                },
            },
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSendMessage(ev) {
        if (!this.chatter.composer) {
            return;
        }
        if (this.chatter.isComposerVisible && !this.chatter.composer.isLog) {
            this.chatter.update({ isComposerVisible: false });
        } else {
            this.chatter.showSendMessage();
        }
    }

}

Object.assign(ChatterTopbar, {
    components,
    props: {
        chatterLocalId: String,
    },
    template: 'mail.ChatterTopbar',
});

return ChatterTopbar;

});
