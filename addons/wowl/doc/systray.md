# Systray

## Overview

The systray is the zone on the right of the navbar that contains various small
components (called _systray items_). These components usually display some sort
of information (like the number of unread messages), notifications and/or let the
user interact with them.

## Systray items

A systray item is an object with the following properties:

- `name (string)`: an unique string describing the systray item (technical name,
  usually prefixed by the current module name)
- `Component`: the Component class that will be used to display the item. Its root
  node has to be a `<li>` tag!
- sequence (number, optional): defaults to 50. If given, this number will be used
  to order the items. The lowest sequence is on the right and the highest sequence
  is on the left in the systray menu.

Warning: the root node need to be a `<li>` tag. Otherwise, the systray item will
not be styled properly.

## Adding a systray item

Once a systray item is defined, adding it to the web client is only a matter of
registering it to the `systrayRegistry`.

For example:

```js
class MySystrayItem extends Component {
  // some component ...
}

const item = {
  name: "myaddon.some_description",
  Component: MySystrayItem,
};

systrayRegistry.add(item.name, Component);
```
