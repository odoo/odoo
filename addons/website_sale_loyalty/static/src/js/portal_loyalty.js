/** @odoo-module **/

import {browser} from "@web/core/browser/browser";
import publicWidget from 'web.public.widget';
import Dialog from 'web.Dialog';
import {_t, qweb} from 'web.core';

publicWidget.registry.LoyaltyPortal = publicWidget.Widget.extend({
    selector: '.o_portal_loyalty',
    xmlDependencies: ['/website_sale_loyalty/static/src/xml/portal_loyalty.xml'],
    events: {
        'click .o_loyalty_redeem_reward_button': '_onClickRedeem',
        'click .o_copy_gift_card_code': '_onClickCopy',
    },

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    _onClickRedeem(ev) {
        const rowEl = ev.target.closest('tr');
        Dialog.confirm(this, _.str.sprintf(_t("Use %(points)s to get '%(name)s'"), {
            points: rowEl.querySelector('.o_loyalty_reward_cost').innerText,
            name: rowEl.querySelector('.o_loyalty_reward_name').innerText,
        }), {
            buttons: [{
                text: _t("Confirm"),
                close: true,
                classes: 'btn-primary',
                click: function () {
                    const rewardId = ev.target.dataset.rewardId;
                    return this._rpc({
                        route: "/my/loyalty/redeem",
                        params: {
                            reward_id: rewardId,
                        },
                    }).then(function (data) {
                        if (data.error) {
                            Dialog.alert(this, data.error);
                        } else {
                            const $content = $('<div/>').append(qweb.render(
                                'website_sale_loyalty.gift_card_info_dialog',
                                data
                            ));
                            const $button = $content.find('button');
                            $button.on('click', (ev) => {
                                browser.navigator.clipboard.writeText(data.code);
                                $button.addClass('disabled');
                                $button.find('#copy_button_text').text(_t('Copied'));
                                $button.off();
                            });
                            Dialog.alert(this, '', {
                                title: _t('Gift card info'),
                                buttons: [{
                                    text: _t("Close"),
                                    close: true,
                                    click: function () {
                                        window.location = '/my/loyalty?tab=redeem_history';
                                    },
                                }],
                                $content: $content,
                                onForceClose: function () {
                                    window.location = '/my/loyalty?tab=redeem_history';
                                },
                            });
                        }
                    });
                },
            }, {
                text: _t("Cancel"),
                close: true,
            }],
        });
    },
    _onClickCopy(ev) {
        browser.navigator.clipboard.writeText(ev.target.closest('button').dataset.code);
        this.displayNotification({
            title: _t("Copied"),
            message: _t("The gift card code has been copied to the clipboard."),
            type: 'success',
        });
    },
});
