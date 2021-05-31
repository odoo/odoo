# Systray

## Overview

The systray is the zone on the right of the navbar that contains various small
components (called _systray items_). These components usually display some sort
of information (like the number of unread messages), notifications and/or let the
user interact with them.

## Systray items

A systray item is simply a component, with a constraint: its root node should be
a `<li>` tag! Otherwise, the systray item will not be styled properly.

## Adding a systray item

Once a systray item is defined, adding it to the web client is only a matter of
registering it to the `systrayRegistry`.

For example:

```js
class MySystrayItem extends Component {
    // some component ...
}

systrayRegistry.add("myaddon.some_description", MySystrayItem);
```

The systray registry is an ordered registry, so one can add a sequence number:

```js
systrayRegistry.add("myaddon.some_description", MySystrayItem, { sequence: 43 });
```

The sequence number defaults to 50. If given, this number will be used
to order the items. The lowest sequence is on the right and the highest sequence
is on the left in the systray menu.
