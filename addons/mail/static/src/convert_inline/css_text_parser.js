/**
 * cssText style property parser, to list propertyNames used in a
 * CSSStyleSheet -> CSSStyleRule -> CSSStyleProperties.
 * This is required because looping over rule.style gives browser standardized
 * keys which are not necessarily the ones used in the written rule, and
 * therefore that loop can not be used to consistently extract values from the
 * written rule.
 * E.g. written `border-radius` will be converted to longhand propertyNames such
 * as `border-top-left-radius` when looped over, then reading the value of that
 * longhand property will return an empty string, which results in a loss of
 * information.
 */
