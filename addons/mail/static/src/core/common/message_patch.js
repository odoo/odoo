import { Composer } from "@mail/core/common/composer";
import { Message } from "@mail/core/common/message";

// Not imported by the message, so that messages can be displayed without the editor.
Object.assign(Message.components, { Composer });
