/** @odoo-module **/

import session from 'web.session';
import core from 'web.core';
const qweb = core.qweb;

/*
* This file provides the necessary mixins that can be used on views to change the behaviour of the help
*  display (no records) in order to provide templates to the user
*/

export const LoyaltyModelMixin = {
    __load: async function () {
        const res = await this._super.apply(this, arguments);

        this.loyaltyTemplateData = await this._rpc({
            model: 'loyalty.program',
            method: 'get_program_templates',
            context: session.user_context,
        });
        return res;
    },

    __get: function () {
        const res = this._super.apply(this, arguments);
        if (res) {
            res.loyaltyTemplateData = this.loyaltyTemplateData;
        }
        return res;
    }
};

export const LoyaltyRendererMixin = {
    _renderNoContentHelper: function (context) {
        this._super.apply(this, arguments);

        if (!this.state.loyaltyTemplateData) {
            return;
        }
        const noContentHelper = this.$('.o_view_nocontent');
        if (noContentHelper) {
            noContentHelper.append(qweb.render('loyalty_program_helper', {
                templateData: this.state.loyaltyTemplateData,
            }));
        }
    },

    _onTemplateClick: async function (ev) {
        ev.stopPropagation();
        const action = await this._rpc({
            model: 'loyalty.program',
            method: 'create_from_template',
            args: [ev.currentTarget.id || ''],
            context: session.user_context,
        });
        if (!action) {
            return;
        }
        this.do_action(action);
    }
};
