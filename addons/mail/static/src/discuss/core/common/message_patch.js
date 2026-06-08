import { Message } from "@mail/core/common/message";
import { MessageSeenIndicator } from "@mail/discuss/core/common/message_seen_indicator";

Message.components = { ...Message.components, MessageSeenIndicator };
