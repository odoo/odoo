import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";

const ALLOWED_SCHEMES = ["http:", "https:", "ftp:", "ftps:"];

/**
 * Normalize a user-typed link the way the server does (`validate_url`):
 * relative paths are made absolute on the current website, scheme-less
 * values are considered as http. Return `null` if the link is not valid.
 *
 * @param {string} value
 * @returns {string|null}
 */
export function normalizeUrl(value) {
    if (value.startsWith("/") && !value.startsWith("//")) {
        return window.location.origin + value;
    }
    const hasScheme = /^[a-z][a-z\d+.-]*:\/\//i.test(value);
    let url;
    try {
        url = new URL(hasScheme ? value : `http://${value}`);
    } catch {
        return null;
    }
    // Credentials are refused: they mostly come from scheme-less values
    // such as "mailto:a@b.com" being parsed as "http://mailto:a@b.com".
    if (!ALLOWED_SCHEMES.includes(url.protocol) || url.username || url.password) {
        return null;
    }
    if (url.hostname !== "localhost" && !url.hostname.includes(".")) {
        return null;
    }
    return value;
}

export class UrlAutoCompleteField extends CharField {
    static template = "website_links.UrlAutoCompleteField";
    static components = {
        ...CharField.components,
        AutoComplete,
    };

    get sources() {
        return [
            {
                optionSlot: "option",
                options: async (term) => {
                    const makeItem = (item) => ({
                        cssClass: "ui-autocomplete-item",
                        label: item.label,
                        onSelect: this.onSelect.bind(this, item.value),
                    });
                    const res = await rpc("/website/get_suggested_links", {
                        needle: term,
                        limit: 15,
                    });
                    const choices = [];
                    for (const page of res.matching_pages) {
                        choices.push(makeItem(page));
                    }
                    for (const other of res.others) {
                        if (other.values.length) {
                            choices.push({
                                cssClass: "ui-autocomplete-category",
                                data: { separator: true },
                                label: other.title,
                            });
                            for (const page of other.values) {
                                choices.push(makeItem(page));
                            }
                        }
                    }
                    return choices;
                },
            },
        ];
    }

    /**
     * Throwing here makes `useInputField` flag the field as invalid, which
     * prevents the record from being saved with a malformed link.
     *
     * @override
     */
    parse(value) {
        value = super.parse(value).trim();
        if (!value) {
            return value;
        }
        const url = normalizeUrl(value);
        if (!url) {
            throw new Error(`Invalid URL: ${value}`);
        }
        return url;
    }

    onSelect(value) {
        this.props.record.update({ [this.props.name]: window.location.origin + value });
    }
}

export const urlAutoComplete = {
    ...charField,
    component: UrlAutoCompleteField,
};

registry.category("fields").add("url_autocomplete", urlAutoComplete);
