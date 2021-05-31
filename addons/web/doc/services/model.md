# Model service

| Technical name | Dependencies  |
| -------------- | ------------- |
| `model`        | `rpc`, `user` |

## Overview

The `model` service is the standard way to interact with a python model, on the
server. Obviously, each such interaction is asynchronous (and will be done by
using the `rpc` service).

In short, the `model` service provides a simple API to call the most common orm
methods, such as `read`, `search_read`, `write` ... It also has a generic `call`
method to call an arbitrary method from the model.

Another interesting point to mention is that the user context will automatically
be added to each model request.

Here is a short example of a few possible ways to interact with the `model`
service:

```ts
class MyComponent extends Component {
    model = useService("model");

    async someMethod() {
        // return all fields from res.partner 3
        const result = await this.model("res.partner").read([3]);

        // create a some.model record with a field name set to 'some name' and a
        // color key set in the context
        const id = await this.model("some.model").create({ name: "some name" }, { color: "red" });

        // perform a read group with some parameters
        const groups = await this.model("sale.order").readGroup(
            [["user_id", "=", 2]],
            ["amount_total:sum"],
            ["date_order"]
        );
    }
}
```

Because the `model` service is a higher level service than `rpc`, easier to use,
and with some additional features, it should be preferred above `rpc`.

## API

The `model` service exports a single function with the following signature:

```ts
function model(modelName: string): Model {
  ...
}
```

A `Model` is here defined as an object linked to the `modelName` odoo model (for
example `res.partner` or `sale.order`) with the following five functions, each
of them bound to `modelName`:

-   `create(state: object, ctx?: Context): Promise<number>`: call the `create` method
    for the `modelName` model defined above,
-   `read(ids: number[], fields: string[], ctx?: Context): Promise<any>`: read one
    or more records
-   `readGroup(domain: any[], fields: string[], groupby: string[], options?: GroupByOptions, ctx?: Context): Promise<ReadGroupResult>;`
-   `searchRead(domain: Domain, fields: string[], options?: SearchReadOptions, ctx?: Context): Promise<SearchReadResult>;`
-   `unlink(ids: number[], ctx?: Context): Promise<void>`
-   `write(ids: number[], data: object, context?: Context): Promise<boolean>`
-   `call(method: string, args?: any[], kwargs?: KWargs): Promise<any>`

## Additional notes

-   since it uses the `rpc` service, it provides the same optimization when used
    by a component: an error will be thrown if a destroyed component attempts to
    initiate a model call, and requests will be left pending if a component is
    destroyed in the meantime.
