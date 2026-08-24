type Translation =
    | string
    | import("@web/core/l10n/translation").Markup
    | import("@web/core/l10n/translation").TranslatedString;

interface ErrorConstructor {
    new (message?: Translation, options?: ErrorOptions): Error;
    (message?: Translation, options?: ErrorOptions): Error;
}
