import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { decorateEmojis } from "@mail/utils/common/format";
import { createElementFromContent, getInnerHtml } from "@mail/utils/common/html";

import { beforeEach, expect, test } from "@odoo/hoot";
import { markup } from "@odoo/owl";

import { makeTestApp, preloadBundle } from "@web/../tests/web_test_helpers";
import { emojiLoader } from "@web/core/emoji_picker/emoji_loader";

const Markup = markup().constructor;

defineMailModels();
preloadBundle("web.assets_emoji");

beforeEach(async () => {
    await makeTestApp();
    await emojiLoader.load();
});

function decoratedHtml(content) {
    return getInnerHtml(decorateEmojis(createElementFromContent(content)));
}

test("emojis in text content are wrapped with title and marked up", async () => {
    const result = decoratedHtml("😇");
    expect(result).toBeInstanceOf(Markup);
    expect(result.toString()).toEqual(
        '<span class="o-mail-emoji" title=":innocent: :halo:">😇</span>'
    );
});

test("emojis in attributes are not wrapped with title", async () => {
    const result = decoratedHtml(markup`<span title='😇'>test</span>`);
    expect(result.toString()).toEqual('<span title="😇">test</span>');
});

test("unsafe content is escaped when wrapping emojis with title", async () => {
    const result = decoratedHtml("<img src='javascript:alert(\"xss\")'/>😇");
    expect(result.toString()).toEqual(
        '&lt;img src=&#x27;javascript:alert(&quot;xss&quot;)&#x27;/&gt;<span class="o-mail-emoji" title=":innocent: :halo:">😇</span>'
    );
});
