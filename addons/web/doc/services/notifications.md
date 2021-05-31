# Notification service

| Technical name  | Dependencies |
| --------------- | ------------ |
| `notifications` |              |

## Overview

Like the name suggests, the `notifications` service allows the rest of the
interface to display notifications (to inform the user of some interesting
relevant facts).

## API

The `notifications` service provides two methods:

-   `create(message: string, options?: Options): number`. This method generates a
    new notification, and returns an `id` value.

    Here is a list of the various options:

    -   `title (string)`: if given, this string will be used as a title
    -   `sticky (boolean)`: if true, this flag states that the notification should only close
        with an action of the user (not close itself automatically)
    -   `type (string)`: can be one of the following: `danger`, `warning`, `success`, `info`.
        These types will slightly alter the color and the icon that will be used
        to draw the notification
    -   `icon (string)`: if no type is given, this string describes a css class that
        will be used. It is meant to use a font awesome class. For example, `fa-cog`
    -   `className (string)`: describes a css class that will be added to the
        notification. It is useful when one needs to add some special style to a
        notification.
    -   `messageIsHtml (boolean)`: if true, the message won't be escaped (false by default)

-   `close(id: string)`: this method will simply close a notification with a specific `id`,
    if it was not already closed.

## Example

Here is how one component can simply display a notification:

```js
class MyComponent extends Component {
    ...
    notifications = useService('notifications');

    ...

    someHandler() {
        this.notifications.create('Look behind you!!!', { sticky: true });
    }
}
```

## Notes

-   whenever the list of notifications is updated, a `NOTIFICATIONS_CHANGE` event is
    triggered on the main bus.
