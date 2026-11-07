# Give every icon `role="img"` and a label or `aria-hidden`

An element that shows an icon (`<i class="oi" data-icon="...">`) carries `role="img"`
and one of:

- `aria-hidden="true"` when the icon is decorative: it repeats the text next to it, or
  it is the content of a button or a link that has its own label. This is the usual
  case.
- `aria-label` when the icon alone tells something, with a `title` for sighted users
  when nothing else on screen says it.

```xml
<!-- decorative: the text says it -->
<a href="#"><i class="oi" data-icon="open_in_new" role="img" aria-hidden="true"/> Open</a>
<!-- icon-only button: the label goes on the button -->
<button class="btn" title="Delete" aria-label="Delete">
    <i class="oi" data-icon="delete" role="img" aria-hidden="true"/>
</button>
<!-- the icon alone tells it -->
<i class="oi" data-icon="lock" role="img" title="Private" aria-label="Private"/>
```

The icon is drawn from the `content` of its `::before` pseudo-element, the ligature
named in `data-icon`, and screen readers read that content: without a label or
`aria-hidden`, they say "open_in_new" or "delete". No role, or `role="presentation"`,
does not stop it. `role="img"` makes the icon one image, that the label names or that
`aria-hidden` removes.

An icon that acts as a button is focusable, so it cannot be `aria-hidden`: write a real
`<button>` with the label, and hide the icon inside it.
