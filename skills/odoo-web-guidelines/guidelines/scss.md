# SCSS and CSS

- Formatting: 4-space indent (no tabs), ~80-column lines, opening brace on the
  selector line, closing brace on its own line, one declaration per line.
- Order properties from the outside in (start at `position`, end with decorative
  rules like `font`/`filter`); put scoped SCSS and CSS variables at the top,
  separated by a blank line.
- Class naming: avoid `id` selectors; prefix classes with `o_<module>` (just
  `o_` for the webclient). Use the flat "grandchild" approach
  (`o_element_entry`), not hyper-specific nested names. Classes use
  underscores (`o_`); SCSS variables, mixins and functions below use hyphens
  (`o-`).
- Variable conventions: SCSS `$o-[root]-[element]-[property]-[modifier]`, scoped
  SCSS `$-[name]`, mixins/functions `o-[name]` (imperative verbs) with
  optional arguments named in scoped form (`@mixin o-avatar($-size: 1.5em)`), CSS variables
  in BEM `--[root]__[element]-[property]--[modifier]`. Don't define CSS variables
  on `:root` (use SCSS for global design; core's few `:root` definitions are
  deliberate utility APIs); CSS variables are for contextual DOM adaptation.
  The variable conventions bind *new* code — much of core (plain mixin
  arguments, `--ComponentName-property` CSS variables) predates them.
