/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { markEventHandled } from "@web/core/utils/misc";

import {
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import {
    formatChar,
    formatInteger,
    formatMonetary,
    formatText,
} from "@web/views/fields/formatters";
import { formatFloat } from "@web/core/utils/numbers";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.userService = useService("user");
        this.avatarCard = usePopover(AvatarCardPopover);
    },
    get authorAvatarAttClass() {
        return {
            ...super.authorAvatarAttClass,
            "o_redirect cursor-pointer": this.hasAuthorClickable(),
        };
    },
    getAuthorText() {
        return this.hasAuthorClickable() ? _t("Open card") : undefined;
    },
    hasAuthorClickable() {
        return this.message.author?.user;
    },
    onClickAuthor(ev) {
        if (this.hasAuthorClickable()) {
            markEventHandled(ev, "Message.ClickAuthor");
            const target = ev.currentTarget;
            if (!this.avatarCard.isOpen) {
                this.avatarCard.open(target, {
                    id: this.message.author.user.id,
                });
            }
        }
    },
    openRecord() {
        this.threadService.open(this.message.originThread);
    },

    /**
     * @returns {string}
     */
    formatTracking(trackingType, trackingValue) {
        switch (trackingType) {
            case "boolean":
                return trackingValue.value ? _t("Yes") : _t("No");
            /**
             * many2one formatter exists but is expecting id/display_name or data
             * object but only the target record name is known in this context.
             *
             * Selection formatter exists but requires knowing all
             * possibilities and they are not given in this context.
             */
            case "char":
            case "many2one":
            case "selection":
                return formatChar(trackingValue.value);
            case "date": {
                const value = trackingValue.value
                    ? deserializeDate(trackingValue.value)
                    : trackingValue.value;
                return formatDate(value);
            }
            case "datetime": {
                const value = trackingValue.value
                    ? deserializeDateTime(trackingValue.value)
                    : trackingValue.value;
                return formatDateTime(value);
            }
            case "float":
                return formatFloat(trackingValue.value);
            case "integer":
                return formatInteger(trackingValue.value);
            case "text":
                return formatText(trackingValue.value);
            case "monetary":
                return formatMonetary(trackingValue.value, {
                    currencyId: trackingValue.currencyId,
                });
            default:
                return trackingValue.value;
        }
    },

    /**
     * @returns {string}
     */
    formatTrackingOrNone(trackingType, trackingValue) {
        const formattedValue = this.formatTracking(trackingType, trackingValue);
        return formattedValue || _t("None");
    },
});
