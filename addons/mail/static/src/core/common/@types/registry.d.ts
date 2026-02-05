declare module "registries" {
    import { ResPartner } from "@mail/core/common/res_partner_model";
    import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";
    import { _t } from "@web/core/l10n/translation";

    type TranslatableString = ReturnType<typeof _t> | string;

    interface IconInfo {
        online: string,
        away: string,
        busy: string,
        offline: string,
        bot?: string,
        default: string,
    }

    interface TitleInfo {
        online: TranslatableString,
        away: TranslatableString,
        busy: TranslatableString,
        offline: TranslatableString,
        bot?: TranslatableString,
        default: TranslatableString,
    }

    interface ImStatusDataItemShape {
        condition: (data: { persona: ResPartner, member: ChannelMember }) => boolean;
        icon: IconInfo | string,
        title: TitleInfo | TranslatableString,
    }

    interface GlobalRegistryCategories {
        "mail.im_status_data": ImStatusDataItemShape;
    }
}
