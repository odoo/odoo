import { describe, expect, test } from "@odoo/hoot";

import {
    formatList,
    jsToPyLocale,
    normalize,
    normalizedMatch,
    pyToJsLocale,
} from "@web/core/l10n/utils";
import { user } from "@web/core/user";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");

describe("formatList", () => {
    test("defaults to the current user's locale", () => {
        patchWithCleanup(user, { lang: "es-ES" });
        const list = ["A", "B", "C"];
        expect(formatList(list)).toBe("A, B y C");
    });

    test("defaults to English if the user's locale can't be retrieved", () => {
        patchWithCleanup(user, { lang: "" });
        const list = ["A", "B", "C"];
        expect(formatList(list)).toBe("A, B, and C");
    });

    test("takes style into account", () => {
        const list = ["A", "B", "C"];
        expect(formatList(list, { style: "or" })).toBe("A, B, or C");
    });

    test("supports “narrow” style with “standard” type", () => {
        const list = ["Veni", "vidi", "vici"];
        expect(formatList(list, { style: "standard-narrow" })).toBe("Veni, vidi, vici");
    });

    test("uses the specified locale", () => {
        const list = ["A", "B", "C"];
        expect(formatList(list, { localeCode: "fr-FR" })).toBe("A, B et C");
    });
});

describe("jsToPyLocale", () => {
    test("2-letter ISO 639 code", () => expect(jsToPyLocale("tg")).toBe("tg"));
    test("3-letter ISO 639 code", () => expect(jsToPyLocale("kab")).toBe("kab"));
    test("language with region", () => expect(jsToPyLocale("fr-BE")).toBe("fr_BE"));
    test("language with region (UN M49 code)", () => expect(jsToPyLocale("es-419")).toBe("es_419"));
    test("language with Latin script", () => expect(jsToPyLocale("sr-Latn")).toBe("sr@latin"));
    test("language with Cyrillic script", () => expect(jsToPyLocale("sr-Cyrl")).toBe("sr@Cyrl"));
    test("language with region and script", () =>
        expect(jsToPyLocale("sr-Latn-RS")).toBe("sr_RS@latin"));
    test("already converted locale", () => expect(jsToPyLocale("fr_TG")).toBe("fr_TG"));
    test("already converted locale with script", () =>
        expect(jsToPyLocale("sr@latin")).toBe("sr@latin"));
    test("undefined locale", () => expect(jsToPyLocale(undefined)).toBe(""));
    test("Tagalog", () => expect(jsToPyLocale("tl-PH")).toBe("tl_PH"));
    test("Filipino", () => expect(jsToPyLocale("fil-PH")).toBe("tl_PH"));
});

describe("pyToJsLocale", () => {
    test("2-letter ISO 639 code", () => expect(pyToJsLocale("tg")).toBe("tg"));
    test("3-letter ISO 639 code", () => expect(pyToJsLocale("kab")).toBe("kab"));
    test("language with region", () => expect(pyToJsLocale("fr_BE")).toBe("fr-BE"));
    test("language with region (UN M49 code)", () => expect(pyToJsLocale("es_419")).toBe("es-419"));
    test("language with Latin script", () => expect(pyToJsLocale("sr@latin")).toBe("sr-Latn"));
    test("language with Cyrillic script", () => expect(pyToJsLocale("sr@Cyrl")).toBe("sr-Cyrl"));
    test("language with region and script", () =>
        expect(pyToJsLocale("sr_RS@latin")).toBe("sr-Latn-RS"));
    test("already converted locale", () => expect(pyToJsLocale("fr-TG")).toBe("fr-TG"));
    test("already converted locale with script", () =>
        expect(pyToJsLocale("sr-Latn")).toBe("sr-Latn"));
    test("undefined locale", () => expect(pyToJsLocale(undefined)).toBe(""));
});

describe("normalize", () => {
    test("diacritics", () => expect(normalize("ž̷̲̺̌a̷̮̳͆̎l̵̯̔̆g̷̭̗̊̑o̷͓̊̓ ̵̜̬̂̅ţ̴̖͒ẹ̵̚x̷̭̪̓t̷̥̒")).toBe("zalgo text"));
    test("diacritics-like", () => expect(normalize("ĦøŧØłð")).toBe("hotold"));
    test("diacritics-like upercase", () => expect(normalize("ØŁÐĦŦ")).toBe("oldht"));
    test("diacritics-like lowercase", () => expect(normalize("øłðħŧ")).toBe("oldht"));
    test("French", () => expect(normalize("éàïœùûîêü")).toBe("eaioeuuieu"));
    test("normalization forms", () =>
        expect(normalize("éÈäÙ".normalize("NFC"))).toBe(normalize("éÈäÙ".normalize("NFD"))));
    test("compatibility equivalence", () => expect(normalize("㎩㎭𝐞")).toBe("parade"));
    test("case folding", () => expect(normalize("Kevin Großkreutz")).toBe("kevin grosskreutz"));
    test(`case folding ( Preserve "Turkish I's")`, () =>
        expect(normalize("Diyarbakır")).toBe("diyarbakir"));
    test("case folding (3)", () => expect(normalize("և")).toBe("եւ"));
    test("ligatures", () => expect(normalize("ŒÆĲ")).toBe("oeaeij"));
    test("ligatures lower case", () => expect(normalize("œæĳ")).toBe("oeaeij"));
    test("empty string", () => expect(normalize("")).toBe(""));
    test("more normalize tests", () => {
        expect(normalize("Երևան")).toBe("երեւան");
        expect(normalize("déçûmes")).toBe("decumes");
        expect(normalize("𝔖𝔥𝔯𝔢𝔨")).toBe("shrek");
        expect(normalize("Scleßin")).toBe("sclessin");
        expect(normalize("Œdipe")).toBe("oedipe");
        // þ (Thorn) is used in Icelandic. It should become "th".
        expect(normalize("Þingvellir")).toBe("thingvellir");
        // đ (D with stroke) is very common. It should become "d".
        expect(normalize("Đà Nẵng")).toBe("da nang");
        // ŋ (Eng) represents a "ng" sound. It should become "n".
        expect(normalize("Siidaŋ")).toBe("siidan");
        expect(normalize("vrĳe")).toBe("vrije"); // using the ĳ ligature
        expect(normalize("Ĳsselmeer")).toBe("ijsselmeer"); // using the Ĳ ligature
        // In Catalan, "ŀ" (U+0140) should be searchable as a standard "l"
        expect(normalize("paral·lel")).toBe("parallel");
        expect(normalize("INTEL·LIGENT")).toBe("intelligent");
        // This is THREE characters: 'l', the middle dot '·', and 'l'.
        expect(normalize("paral·lel")).toBe("parallel");
        // French accents
        expect(normalize("Cédric")).toBe("cedric");
        expect(normalize("Noël")).toBe("noel");
        // The ñ in spanish
        expect(normalize("niño")).toBe("nino");
        // İstanbul (with dot) starts with İ (U+0130)
        expect(normalize("İstanbul")).toBe("istanbul");
        // Diyarbakır (without dot) ends with ı (U+0131)
        expect(normalize("Diyarbakır")).toBe("diyarbakir");

        // Mathematical bold/italic (often from copy-paste)
        expect(normalize("𝐛𝐨𝐥𝐝")).toBe("bold");

        // Non-breaking spaces (U+00A0) should be treated as normal spaces
        // Use a literal non-breaking space here or \u00A0
        expect(normalize("John\u00A0Doe")).toBe("john doe");

        expect(normalize("long-word")).toBe("long-word");
        // The "Soft Hyphen" (U+00AD) - Invisible in many UI's but breaks 'indexOf'
        expect(normalize("soft\u00ADhyphen")).toBe("softhyphen");

        // Ensure the shield doesn't accidentally prevent lowercasing
        // of standard uppercase strings.
        expect(normalize("ODOO")).toBe("odoo");

        // Ensure it correctly triggers the 'heavy' logic when a symbol appears
        expect(normalize("Odoo™")).toBe("odootm");
    });
    test("Hindi (Devanagari): should preserve vowel marks", () => {
        // 'नमस्ते' (Namaste) contains 'म' (ma) + 'स' (sa) + '्' (Virama) + 'त' (ta) + 'े' (vowel e)
        // If we use \p{M} or \p{Diacritic}, it might become 'नमसत' (Nmsat) - which is wrong.
        const hindi = "नमस्ते";
        expect(normalize(hindi)).toBe(hindi); // Should remain identical (lowercased if applicable)
    });

    test("Thai: should preserve tone and vowel marks", () => {
        // 'สวัสดี' (Sawasdee)
        // Stripping marks would turn 'ดี' (dee) into 'ด' (d), losing the vowel 'ี'.
        const thai = "สวัสดี";
        expect(normalize(thai)).toBe(thai);
    });

    test("Combined Latin and Hindi", () => {
        // Tests that the logic can handle mixed strings correctly
        // 'Café' should be cleaned, 'नमस्ते' should stay intact.
        expect(normalize("Café नमस्ते")).toBe("cafe नमस्ते");
    });
});

describe("normalizedMatch", () => {
    test("plain ASCII inputs", () => {
        const { start, end, match } = normalizedMatch("Yuchen (yhu)", "yhu");
        expect(match).toBe("yhu");
        expect(start).toBe(8);
        expect(end).toBe(11);
    });
    test("compatibility equivalence", () => {
        const { start, end, match } = normalizedMatch("𝔖𝔥𝔯𝔢𝔨", "SHRE");
        expect(match).toBe("𝔖𝔥𝔯𝔢");
        expect(start).toBe(0);
        expect(end).toBe(8);
        expect("𝔖𝔥𝔯𝔢𝔨".slice(start, end)).toBe(match);
    });
    test("some fancy letters without canonical decomposition", () => {
        const { start, end, match } = normalizedMatch("Bjørn Dæhlie", "ORN DAE");
        expect(start).toBe(2);
        expect(end).toBe(8);
        expect(match).toBe("ørn Dæ");
    });
    describe("ligatures", () => {
        test("in source string", () => {
            const { start, end, match } = normalizedMatch("Richard Cœur de Lion", "coeur");
            expect(start).toBe(8);
            expect(end).toBe(12);
            expect(match).toBe("Cœur");
        });
        test("in substring", () => {
            const { start, end, match } = normalizedMatch("Džemal Bijedić", "ǆ");
            expect(start).toBe(0);
            expect(end).toBe(2);
            expect(match).toBe("Dž");
        });
        test("substring ends in the middle of a ligature", () => {
            const { start, end, match } = normalizedMatch("Æthelflæd", "aethelfla");
            expect(start).toBe(0);
            expect(end).toBe(8);
            expect(match).toBe("Æthelflæ");
        });
    });
    describe("full case folding", () => {
        test("in source string", () => {
            const { start, end, match } = normalizedMatch("Scleßin", "essi");
            expect(start).toBe(3);
            expect(end).toBe(6);
            expect(match).toBe("eßi");
        });
        test("in substring", () => {
            const { start, end, match } = normalizedMatch("Sclessin", "eßi");
            expect(start).toBe(3);
            expect(end).toBe(7);
            expect(match).toBe("essi");
        });
    });
    describe("diacritics", () => {
        test("accent on last letter", () => {
            const { start, end, match } = normalizedMatch("José Bové", "vé");
            expect(start).toBe(7);
            expect(end).toBe(9);
            expect(match).toBe("vé");
        });
        test("normalization form is preserved", () => {
            const { start, end, match } = normalizedMatch(
                "eĥoŝanĝo ĉiuĵaŭde".normalize("NFD"),
                "EHOSANGO CIUJAUDE"
            );
            expect(start).toBe(0);
            expect(end).toBe(23);
            expect(match).toBe("eĥoŝanĝo ĉiuĵaŭde");
        });
        test("Ph'nglui mglw'nafh Cthulhu R'lyeh wgah'nagl fhtagn", () => {
            const { start, end, match } = normalizedMatch("N̸̟̤̦̥̦͚̘̟̙͓͚̱͇̱͍̦͓͕̝͈̣̺͔̐͂͑̂̅̇̄̏͐̒̾̋̿̀̐̎̄͗̀͋̈́̉̈́͑̋͊̃̃̃͌̃́̚̚͝͝y̸̢̢̢̧͙̳̫̙̺̝͔̭̲̮͎̦͈͉͚̣̖̞̳͙͚͕̪̘̓̓̇͗͑̈͋͑̅̒̎̄̉̊͌̂̈́̏̚͜ͅͅa̶̧̡͕̝̥̝̳̬̙͔̱͎̠̍͌̓͆̾̔̾͐͌̀̔̀̽̓͐̽͒̌̽̀͗͗͋̉̒̒̎͌͘̚̚͜͝͠ř̴͇͒̀̑̊́̓̈́̎̆̈́̾̅̾̈̃̉̂̄͋̄͑̇̃̽̽͌̐̀̉̃̀͛̂̓̄͑͆̋̌̕͘̚̕͘̕͠͝l̷̢͈̙͕͝a̴̧̨̢̧̧̧̨̨̛̛̰̙̹̭̻̘̤̪͎̯͈͙̻͕̜̹̲͎̜͔̻̟͉̾̾͑́̍͆́͛̍̀͛̂͂͑͒͜͝ţ̵̨̩̞̦̺̯̱̝̻̹̜̩͙̮̤̘̟͉͉̘̩̻̠̻̜͖̗̝͓̝͖͚̜̥͍̠̗̰̦̱͔̤̣̮͔̿̓͒̍̈́̀̔̌̐̉͋̌̋͐̅̈́͘͜ȟ̶̢̧̦͔̞̺̮͎̻̣̪̮̣̱̮̤͇͈͖̮̯̝̩̻̄͂͊̈́͂̀̎́̊͌̒̉̊̓̊̀̂̆̋̚͜͠ǫ̸̤̪̜̲̠͕̮͔̜͔͚̺̠̲͇͓̺̣̣̗̭̠̫̓͗̽͋͘͜͠ţ̸̧̨̨̨̛̛̩̫̫̟̣͍̭̯͕̩͖̝̜̱͖͈̯̺̞̬̮̱̲̦͎̠̤̟̖͓͎̹̦̭̖̲̞̱̹̬̯̗͈̓̈́̎͒̒̔̎͑͐͛̄̊͛́̈́̄̾͛̒̒̑́̎͌̌̏̐̑͗̊̈́̀͌̂̏̀́̚͘͝ȩ̴̨̢̛̛̦̥̤̟̣͇̱̜̥̠̦̻̳̼̣̜̺̼̼̝̳͖͙͍̗̦͕̼̟̟̹̹̝̣̮̜͓̜̼̺̺̈́̍̐̽̔́̾̓̔̅̿̽͊̈͒̊̓̔̏̐̐̽̄̈́͑̌̉̉͘͘p̴̡̡̨̧̛̜̫̠͉̜̯͍̩̠̥̩̣̩̲̦̗͚̗̲͕̾̀͗̊̀̊͛̐̽͌̎̊̎̑̍́̓̒̅̉͗̐̿̊̃͋́͂̍͆͂͘̕͜͠", "nya");
            expect(start).toBe(0);
            expect(end).toBe(115);
            expect(match).toBe("N̸̟̤̦̥̦͚̘̟̙͓͚̱͇̱͍̦͓͕̝͈̣̺͔̐͂͑̂̅̇̄̏͐̒̾̋̿̀̐̎̄͗̀͋̈́̉̈́͑̋͊̃̃̃͌̃́̚̚͝͝y̸̢̢̢̧͙̳̫̙̺̝͔̭̲̮͎̦͈͉͚̣̖̞̳͙͚͕̪̘̓̓̇͗͑̈͋͑̅̒̎̄̉̊͌̂̈́̏̚͜ͅͅa");
        });
    });
    describe("corner cases", () => {
        test("empty source string", () => {
            const { start, end, match } = normalizedMatch("", "Œdipe Roi");
            expect(start).toBe(-1);
            expect(end).toBe(-1);
            expect(match).toBe("");
        });
        test("empty substring", () => {
            const { start, end, match } = normalizedMatch("泽龙", "");
            expect(start).toBe(0);
            expect(end).toBe(0);
            expect(match).toBe("");
        });
        test("empty inputs", () => {
            const { start, end, match } = normalizedMatch("", "");
            expect(start).toBe(0);
            expect(end).toBe(0);
            expect(match).toBe("");
        });
        test("matches last character", () => {
            const { start, end, match } = normalizedMatch("雨晨", "晨");
            expect(start).toBe(1);
            expect(end).toBe(2);
            expect(match).toBe("晨");
        });
    });
});
