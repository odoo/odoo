import { prettifyMessageContent } from "../../src/utils/common/format";

import { describe, expect, test } from "@odoo/hoot";

describe.current.tags("headless");

function format(str, args) {
    return str.replace(/\{(\d+)\}/g, (_, index) => args[index]);
}

function getLink(recordType, record) {
    switch(recordType) {
        case 'partners':
            return `<a href="/odoo/res.partner/${record.id}" class="o_mail_redirect" data-oe-id="${record.id}" data-oe-model="res.partner" target="_blank" contenteditable="false">@${record.name}</a>`;
        case 'threads':
            let className, text;
            if (record.parent_channel_id) {
                className = "o_channel_redirect o_channel_redirect_asThread";
                text = `#${record.parent_channel_id.displayName} &gt; ${record.displayName}`;
            } else {
                className = "o_channel_redirect";
                text = `#${record.displayName}`;
            }
            return `<a href="/odoo/discuss.channel/${record.id}" class="${className}" data-oe-id="${record.id}" data-oe-model="discuss.channel" target="_blank" contenteditable="false">${text}</a>`;
    }
}

function getDisplayedText(recordType, record) {
    switch(recordType) {
        case 'partners':
            return "@" + record.name;
        case 'threads':
            return record.parent_channel_id ? `#${record.parent_channel_id.displayName} > ${record.displayName}` : `#${record.displayName}`;
    }
}

function testPrettifyMessageContentMentions(recordType, records, messageTemplate) {
    const recordsText = records.map(r => getDisplayedText(recordType, r));
    test(`prettifyMessageContent properly replace ${recordType} mentions for ${recordsText.join(", ")}`, async () => {
        const body = format(messageTemplate, recordsText);
        const res = format(messageTemplate, records.map(r => getLink(recordType, r)));
        const prettified = await prettifyMessageContent(body, {[recordType]: records});
        expect(prettified.toString()).toBe(res);
    })
}

const partnerMessageTemplate = '{1} says hello to {0}';
testPrettifyMessageContentMentions('partners', [{id: 1, name: 'Bernard'}, {id: 12, name: 'Isabelle'}], partnerMessageTemplate);

const threadMessageTemplate = 'There may be answers here {1} or here {0}';
testPrettifyMessageContentMentions('threads', [{id: 1, displayName: 'Best beer in Belgium'}, {id: 18, displayName: 'Cutest cats'}], threadMessageTemplate);
