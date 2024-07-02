import { Chatter } from "@mail/chatter/web_portal/chatter";

Chatter.template = "portal.Chatter";

Chatter.props.push("composer?", "twoColumns?");

Object.assign(Chatter.defaultProps, { composer: true });
