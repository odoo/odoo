# Hooks

## Overview

- [useBus](#usebus)

## useBus

This hook ensures a bus is properly used by a component:

- each time the component is **mounted**, the callback registers on the bus,
- each time the component is **unmounted**, the callback unregisters off the bus.

### API

> ```ts
> useBus(bus: EventBus, eventName: string, callback: Callback): void
> ```
>
> where

- `bus` is the event bus to use.
- `eventName` is the event name to register a callback for.
- `callback` gets called when the `bus` dispatches an `eventName` event.

### Example

```js
class MyComponent extends Component {
  constructor() {
    super(...arguments);
    useBus(this.env.bus, "some-event", this.myCallback);
  }
  myCallback() {
    // ...
  }
}
```
