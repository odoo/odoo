# QWeb PDF reports

- A custom report's `_get_report_values` must add the default `docs` / `doc_ids`
  / `doc_model` itself if the template needs them — they are not auto-included.
- For translated reports use `t-lang` — it is only valid on a node that also
  carries `t-call` (anywhere else QWeb raises a `SyntaxError` at template
  compile time); to translate part of a report,
  extract that part into its own template and `t-call` it with `t-lang`. Only
  re-browse records in the target language when the template reads
  translatable fields (otherwise it is a needless performance cost).
