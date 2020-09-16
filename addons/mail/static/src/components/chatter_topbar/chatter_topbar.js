odoo.define('mail/static/src/components/chatter_topbar/chatter_topbar.js', function (require) {
'use strict';

const components = {
    FollowButton: require('mail/static/src/components/follow_button/follow_button.js'),
    FollowerListMenu: require('mail/static/src/components/follower_list_menu/follower_list_menu.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;

class ChatterTopbar extends Component {

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
            __mfield_isAttachmentBoxVisible: !this.chatter.__mfield_isAttachmentBoxVisible(this),
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
        if (!this.chatter.__mfield_composer(this)) {
            return;
        }
        if (this.chatter.__mfield_isComposerVisible(this) && this.chatter.__mfield_composer(this).__mfield_isLog(this)) {
            this.chatter.update({ __mfield_isComposerVisible: false });
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
                default_res_id: this.chatter.__mfield_threadId(this),
                default_res_model: this.chatter.__mfield_threadModel(this),
            },
            res_id: false,
        };
        return this.env.bus.trigger('do-action', {
            action,
            options: {
                on_close: () => {
                    this.chatter.refreshActivities();
                    this.chatter.refresh();
                },
            },
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSendMessage(ev) {
        if (!this.chatter.__mfield_composer(this)) {
            return;
        }
        if (this.chatter.__mfield_isComposerVisible(this) && !this.chatter.__mfield_composer(this).__mfield_isLog(this)) {
            this.chatter.update({ __mfield_isComposerVisible: false });
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
