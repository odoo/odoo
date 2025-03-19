import { wrapEmojisWithTitles } from "@mail/utils/common/format";
import { expect, test } from "@odoo/hoot";
import { markup } from "@odoo/owl";
import { makeMockEnv } from "@web/../tests/web_test_helpers";
import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";
const Markup = markup().constructor;

test("emojis in text content are wrapped with title and marked up", async () => {
    await makeMockEnv();
    await loadEmoji();
    const result = wrapEmojisWithTitles("😇");
    expect(result).toBeInstanceOf(Markup);
    expect(result.toString()).toEqual('<span title=":innocent: :halo:">😇</span>');
});

test("emojis in attributes are not wrapped with title", async () => {
    await makeMockEnv();
    await loadEmoji();
    const result = wrapEmojisWithTitles(markup("<span title='😇'>test</span>"));
    expect(result.toString()).toEqual('<span title="😇">test</span>');
});

test("unsafe content is escaped when wrapping emojis with title", async () => {
    await makeMockEnv();
    await loadEmoji();
    const result = wrapEmojisWithTitles("<img src='javascript:alert(\"xss\")'/>😇");
    expect(result.toString()).toEqual(
        '&lt;img src=\'javascript:alert("xss")\'/&gt;<span title=":innocent: :halo:">😇</span>'
    );
});
