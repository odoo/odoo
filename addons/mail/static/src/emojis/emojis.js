/** @odoo-module */

/**
 * When the mail module has the new env, it would be better to make this a service. 
 * Most of it doesn't even require to be a service as it is static content, 
 * but two functions needs the env and are currently getting it through parameters.
 * There is no reason this becomes a model. 
 */

import { rawEmojis as data } from "@mail/emojis/emojis_source" 

/**
 * Helper to get the code point string from a unicode.
 * The code point is simply an ascii hexadecimal representation of the unicode value.
 * We use the code point value for the scss class names of the emoji sprites.
 */
function unicodeToCodePoint(unicodeSurrogates, sep = "-") {
  var r = [],
    c = 0,
    p = 0,
    i = 0;
  while (i < unicodeSurrogates.length) {
    c = unicodeSurrogates.charCodeAt(i++);
    if (p) {
      r.push((0x10000 + ((p - 0xd800) << 10) + (c - 0xdc00)).toString(16));
      p = 0;
    } else if (0xd800 <= c && c <= 0xdbff) {
      p = c;
    } else {
      r.push(c.toString(16));
    }
  }
  return r.join(sep);
}

/**
 * This code take the raw emoji source array and performs all the operations needed to get it
 * to the format odoo used. 
 */
const nestedMapOfCategorizedEmojis = {};
for (const category in data) {
  for (const emoji of data[category]) {
    emoji.category = category;

    if (!(category in nestedMapOfCategorizedEmojis)) {
      nestedMapOfCategorizedEmojis[category] = {};
    }

    if (!(emoji.unicode in nestedMapOfCategorizedEmojis[category])) {
      nestedMapOfCategorizedEmojis[category][emoji.unicode] = {
        sources: emoji.codes,
        unicode: emoji.unicode,
        description: emoji.description,
        category: emoji.category,
        codePoint: unicodeToCodePoint(emoji.unicode),
      };
    } else {
      if (
        !nestedMapOfCategorizedEmojis[category][emoji.unicode].sources.includes(
          emoji.code
        )
      ) {
        nestedMapOfCategorizedEmojis[category][emoji.unicode].sources.push(
          emoji.code
        );
      }
    }
  }
}

/**
 * Get all the emojis categories
 */
export function getEmojisCategories() {
  return Object.keys(nestedMapOfCategorizedEmojis);
}

/**
 * Get all the emojis as a map with the keys being the unicode emojis.
 */
function getAllEmojisAsMap() {
  let res = {};
  for (const category of getEmojisCategories()) {
    res = { ...res, ...nestedMapOfCategorizedEmojis[category] };
  }
  return res;
}
export const emojisAsMap = getAllEmojisAsMap();

/**
 * Get all the emojis of one category as an array
 */
export function getEmojiesFromCategoryAsArray(category) {
  return Object.values(nestedMapOfCategorizedEmojis[category]);
}

/**
 * How many emojis should we keep for the recently used feature of the popover.
 */
const recentlyUsedEmojisLimit = 10;

/**
 * Keep in browser cache what unicode emoji have been recently used.
 */
export function setLastUsedEmoji(env, unicode) {
  if (!isUnicodeInOdooEmojisSelection(unicode)) return; // don't keep emojis we don't have in our selection
  const usedEmojis = env.services.local_storage.getItem("usedEmojis", {});
  usedEmojis[unicode] = Date.now(); // Timestamp
  if (Object.keys(usedEmojis).length > recentlyUsedEmojisLimit) {
    let oldest = null;
    for (let unicode in usedEmojis) {
      if (oldest == null) oldest = unicode;
      if (usedEmojis[unicode] > oldest) {
        oldest = unicode;
      }
    }
    delete usedEmojis[oldest];
  }
  env.services.local_storage.setItem("usedEmojis", usedEmojis);
}

export function getRecentlyUsedEmojis(env) {
  const usedEmojisMap = env.services.local_storage.getItem("usedEmojis", {});
  return Object.entries(usedEmojisMap)
    .sort((a, b) => b[1] - a[1])
    .map((el) => emojisAsMap[el[0]]);
}

/**
 * Used to make sure an emoji is in our selection, meaning we can 
 * display it with a sprite.
 */
export function isUnicodeInOdooEmojisSelection(unicode) {
  const emoji = emojisAsMap[unicode];
  return Boolean(emoji);
}

/**
 * Get back an emoji object by providing a unicode.
 * Be sure to call isUnicodeInOdooEmojisSelection first if it is not certain
 * the emoji exist in our selection. 
 */
export function getEmoji(unicode) {
  return emojisAsMap[unicode];
}

/**
 * Get the css class required to display an emoji with the sprite system.
 * The sprites being displayed as background images.
 */
export function getEmojiClassName(emoji) {
  return "o-emoji-" + emoji.codePoint;
}


/**
 * Get all the emojis as an array
 */
 function getAllEmojisAsArray() {
  return Object.values(emojisAsMap);
}

/**
 * A simple list of all the emojis
 */
export const emojis = getAllEmojisAsArray();

/**
 * This regex comes from the official BNF grammar.
 * https://unicode.org/reports/tr51/#EBNF_and_Regex
 * It let us parse a string to find all emojis. It is pretty complex as emojis can be composed of several parts (like the concept of variants by example)
 */
const pattern = /\p{RI}\p{RI}|\p{Emoji}(\p{Emoji_Modifier}|\u{FE0F}\u{20E3}?|[\u{E0020}-\u{E007E}]+\u{E007F})?(\u{200D}\p{Emoji}(\p{Emoji_Modifier}|\u{FE0F}\u{20E3}?|[\u{E0020}-\u{E007E}]+\u{E007F})?)*/gu; 
export const matchUnicodeEmojiPattern = pattern;

/**
 * Legacy emojis are kept here and are still available for places that don't support the new system yet. 
 * (like in text content that can't display an image but won't display the emoji source neither)
 */
const legacyEmojisUnicodes = [ "😊", "😃", "😆", "😂", "😉", "😎", "😜", "😋", "😝", "😳", "😐", "😕", "😞", "😱", "😲", "😨", "😠", "😈", "😘", "😇", "😢", "😭", "❤️", "💔", "😍", "👳", "👍", "👎", "👌", "💩", "🙈", "🙉", "🙊", "🐞", "😺", "🐻", "🐌", "🐗", "🍀", "🌹", "🔥", "☀️", "⛅️", "🌈", "☁️", "⚡️", "⭐️", "🍪", "🍕", "🍔", "🍟", "🎂", "🍰", "☕️", "🍌", "🍣", "🍙", "🍺", "🍷", "🍸", "🍹", "🍻", "👻", "💀", "👽", "👽", "🎉", "🏆", "🔑", "📌", "📯", "🎵", "🎺", "🎸", "🏃", "🚲", "⚽️", "🏈", "🎱", "🎬", "🎤", "🧀"];
const legacyEmojisArray = [];
for (const unicode of legacyEmojisUnicodes) {
  if (isUnicodeInOdooEmojisSelection(unicode)) {
    legacyEmojisArray.push(getEmoji(unicode));
  }
}
export const legacyEmojis = legacyEmojisArray;
