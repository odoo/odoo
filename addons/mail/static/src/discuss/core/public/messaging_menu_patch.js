import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu";
import { PublicSelfMenu } from "@mail/discuss/core/public/public_self_menu";

MessagingMenu.components = { ...MessagingMenu.components, PublicSelfMenu };
