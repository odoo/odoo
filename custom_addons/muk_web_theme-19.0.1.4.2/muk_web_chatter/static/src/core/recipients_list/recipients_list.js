import { Component, markup } from '@odoo/owl';

import { _t } from '@web/core/l10n/translation';
import { escape } from '@web/core/utils/strings';
import { formatList } from '@web/core/l10n/utils';
import { usePopover } from '@web/core/popover/popover_hook';

import { RecipientsListPopover } from '@muk_web_chatter/core/recipients_popover/recipients_popover';

export class RecipientsList extends Component {
    static template = 'muk_web_chatter.BaseRecipientsList';
    static props = {
        thread: { type: Object },
        internalOnly: { type: Boolean, optional: true },
    };
    setup() {
        this.recipientsPopover = usePopover(
            RecipientsListPopover, { position: 'bottom-start' }
        );
    }
    get recipients() {
        let result = [...this.props.thread?.recipients].filter(
            (r) => r.partner_id
        );
        if (this.props.internalOnly === true) {
            result = result.filter(
                (r) => (
                    r.partner_id.main_user_id && 
                    r.partner_id.main_user_id.share === false
                )
            );
        }
        return result;
    }
    get hasMore() {
        return this.recipients.length > 3;
    }
    getRecipientsSummary() {
        const items = this.recipients.slice(0, 3).map(({ partner_id }) => {
            const email = partner_id.email || '';
            const title = email || _t('no email address');
            const emailWithoutDomain = (
                email.includes('@') ? email.split('@', 1)[0] : email
            );
            const text = email ? emailWithoutDomain : partner_id.name;
            return `<span title='${escape(title)}'>${escape(text)}</span>`;
        });
        if (this.hasMore) {
            items.push(escape(
                _t('%(recipientCount)s more', {
                    recipientCount: this.recipients.length - 3,
                })
            ));
        }
        return markup(formatList(items));
    }
    onClickMore(ev) {
        ev.stopPropagation();
        if (this.recipientsPopover.isOpen) {
            this.recipientsPopover.close();
        } else {
            this.recipientsPopover.open(ev.currentTarget, {
                recipients: this.recipients,
            });
        }
    }
}
