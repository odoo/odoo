import { describe, expect, test } from "@odoo/hoot";
import { prepareSeoMetadataValues } from "@website/components/dialog/seo";

describe.current.tags("headless");

const metadata = {
    title: "Fresh bread in Brussels",
    description: "Sourdough baked every morning.",
    keywords: ["bakery", "sourdough"],
};

test("prepares the metadata values of an editable page", () => {
    const data = {
        can_edit_seo: true,
        default_lang_code: "en_US",
        website_meta_title: "",
        website_meta_description: "",
        website_meta_keywords: "",
    };
    expect(prepareSeoMetadataValues(data, metadata, "en_US")).toEqual({
        website_meta_title: "Fresh bread in Brussels",
        website_meta_description: "Sourdough baked every morning.",
        website_meta_keywords: "bakery,sourdough",
    });
});

test("only prepares the fields the record can hold", () => {
    const data = {
        can_edit_seo: false,
        default_lang_code: "en_US",
        website_meta_title: "",
        website_meta_keywords: "",
    };
    expect(prepareSeoMetadataValues(data, metadata, "en_US")).toEqual({
        website_meta_keywords: "bakery,sourdough",
    });
});

test("does not use a translation as source when the default language is empty", () => {
    const data = {
        can_edit_seo: true,
        default_lang_code: "en_US",
        website_meta_title: "",
        website_meta_description: "",
        website_meta_keywords: "",
        default_website_meta_title: "Bakery",
    };
    expect(prepareSeoMetadataValues(data, metadata, "fr_BE")).toEqual({
        website_meta_title: "Fresh bread in Brussels",
        website_meta_description: { en_US: "", fr_BE: "Sourdough baked every morning." },
        website_meta_keywords: { en_US: "", fr_BE: "bakery,sourdough" },
    });
});
