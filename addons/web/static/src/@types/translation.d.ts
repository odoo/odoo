type TranslatedString =
    | string
    | import("@web/core/l10n/translation").Markup
    | import("@web/core/l10n/translation").LazyTranslatedString;

interface ErrorConstructor {
    new (message?: TranslatedString, options?: ErrorOptions): Error;
    (message?: TranslatedString, options?: ErrorOptions): Error;
}
