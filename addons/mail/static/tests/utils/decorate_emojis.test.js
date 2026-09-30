import { decorateEmojis } from "@mail/utils/common/format";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

import { expect, test } from "@odoo/hoot";
import { markup } from "@odoo/owl";

import { makeMockEnv } from "@web/../tests/web_test_helpers";
import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";

const Markup = markup().constructor;

defineMailModels();

test("emojis in text content are wrapped with title and marked up", async () => {
    await makeMockEnv();
    await loadEmoji();
    const result = decorateEmojis("😇");
    expect(result).toBeInstanceOf(Markup);
    expect(result.toString()).toEqual(
        '<span class="o-mail-emoji" title=":innocent: :halo:">😇</span>'
    );
});

test("emojis in attributes are not wrapped with title", async () => {
    await makeMockEnv();
    await loadEmoji();
    const result = decorateEmojis(markup`<span title='😇'>test</span>`);
    expect(result.toString()).toEqual('<span title="😇">test</span>');
});

test("unsafe content is escaped when wrapping emojis with title", async () => {
    await makeMockEnv();
    await loadEmoji();
    const result = decorateEmojis("<img src='javascript:alert(\"xss\")'/>😇");
    expect(result.toString()).toEqual(
        '&lt;img src=\'javascript:alert("xss")\'/&gt;<span class="o-mail-emoji" title=":innocent: :halo:">😇</span>'
    );
});
