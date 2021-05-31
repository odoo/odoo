# Main Components

A common need for a feature is the ability to interact with the DOM, somewhere
at the root of the web client. For example, the notification service want to
include a component somewhere to be able to display notifications. Or maybe the
discuss code will need the ability to display chat windows.

The Odoo javascript framework provides a way to do that, with the idea of
`main components`. These are component classes (NOT instances) that are registered
in the `mainComponentRegistry`. For example:

```ts
class MyComponent extends Component {
    ...
}

componentRegistry.add("myaddon.MyComponent", MyComponent);
```

When the web client is rendered, it will iterate over all these Component and
add them to a `div` inside its template.

Notes:

-   like usual, it is a convention to prefix the registry keys with the name of
    the odoo addon that register it, in order to lessen the risk of name collision.
-   Since these components are rendered when the Web client is started, they can
    actually delay the rendering (if they implement `willStart`). Therefore, one
    need to be cautious. If possible, try to keep them synchronous.
