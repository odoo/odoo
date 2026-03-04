import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';

import { Composer } from '@mail/core/common/composer';

patch(Composer.prototype, {
    get SEND_TEXT() {
        if (
            this.props.type === 'note' &&
            this.props.notifyInternalFollowers
        ) {
            return _t('Send');
        }
        return super.SEND_TEXT;
    },
    get placeholder() {
        if (
            this.props.type === 'note' &&
            this.props.notifyInternalFollowers
        ) {
            return _t('Send a message to internal followers...');
        }
        return super.placeholder;
    },
    get postData() {
        const postData = super.postData;
        postData.notifyInternalFollowers = (
            this.props.notifyInternalFollowers || false
        );
        return postData;
    },
});

Composer.props = [...Composer.props, 'notifyInternalFollowers?'];
