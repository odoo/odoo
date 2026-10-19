declare module "registries" {
    import { ChannelMember, MailGuest, ResPartner, ResUsers } from "models";
    import { _t } from "@web/core/l10n/translation";

    type TranslatableString = ReturnType<typeof _t> | string;

    interface IconInfo {
        online: string;
        away: string;
        busy: string;
        offline: string;
        bot?: string;
        default: string;
    }

    interface TitleInfo {
        online: TranslatableString;
        away: TranslatableString;
        busy: TranslatableString;
        offline: TranslatableString;
        bot?: TranslatableString;
        default: TranslatableString;
    }

    interface ImStatusData {
        icon: string;
        iconClass: string;
        title: TranslatableString;
    }

    interface ImStatusDataRegistryItem {
        condition: (data: {
            persona: MailGuest | ResPartner,
            member?: ChannelMember,
            user?: ResUsers,
        }) => boolean;
        icon: IconInfo | string;
        iconClass: IconInfo | string;
        title: TitleInfo | TranslatableString;
    }

    interface PartnerCompareDataItemShape {
        (p1: ResPartner, p2: ResPartner, options: {
            context: {
                memberPartnerIds?: Set<number>,
                recentChatPartnerIds?: number[],
            },
            searchTerm?: string;
            store: import("models").Store,
            thread?: import("models").Thread,
        }): number;
    }

    interface GlobalRegistryCategories {
        "mail.im_status_data": ImStatusDataRegistryItem;
        "mail.partner_compare": PartnerCompareDataItemShape;
    }
}
